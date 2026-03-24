from PySide6.QtCore import QThread, Signal
import time
from eeg_brainlink import BrainLinkEEG, BrainLinkData

class EEGInput(QThread):
    data_signal = Signal(dict)
    status_signal = Signal(str)

    def __init__(self, port='COM5', baudrate=57600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.eeg = None
        self.auto_scan = False # Flag para o run()

    def _on_data(self, data: BrainLinkData):
        """Callback para receber dados do parser e emitir sinal Qt"""
        # Debug log para o EEG
        print(f"DEBUG EEG: Att: {data.attention:3d} | Med: {data.meditation:3d} | Sig: {data.signal:3d}")
        
        self.data_signal.emit({
            "attention": data.attention,
            "meditation": data.meditation,
            "signal": data.signal,
            "battery": data.battery,
            "waves": {
                "delta": data.delta,
                "theta": data.theta,
                "alpha": (data.low_alpha + data.high_alpha) / 2,
                "beta": (data.low_beta + data.high_beta) / 2,
                "gamma": (data.low_gamma + data.high_gamma) / 2
            },
            "timestamp": time.time()
        })

    def run(self):
        import serial.tools.list_ports
        available = serial.tools.list_ports.comports()
        
        ports_to_try = [self.port] if self.port else []
        if self.auto_scan:
            # BrainLink costuma ser um link Bluetooth
            for p in available:
                if p.device != self.port:
                    if "bluetooth" in p.description.lower() or "brainlink" in p.description.lower():
                        ports_to_try.insert(0, p.device)
                    else:
                        ports_to_try.append(p.device)

        for port in ports_to_try:
            try:
                self.status_signal.emit(f"Tentando EEG em {port}...")
                self.eeg = BrainLinkEEG(port=port, baudrate=self.baudrate)
                if self.eeg.connect():
                    self.eeg.add_callback(self._on_data)
                    self.port = port
                    self.status_signal.emit(f"BrainLink conectado na {port}")
                    self.running = True
                    break
            except Exception:
                continue
        
        if self.running:
            while self.running:
                self.eeg.read_once() 
                time.sleep(0.01)
        else:
            self.status_signal.emit("Falha ao encontrar BrainLink.")
            self.stop()

    def stop(self):
        self.running = False
        if self.eeg:
            self.eeg.disconnect()
        self.status_signal.emit("EEG desconectado")
        self.quit()
