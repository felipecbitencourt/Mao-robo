from PySide6.QtCore import QThread, Signal
import time
from hardware.eeg_brainlink import BrainLinkEEG, BrainLinkData

class EEGInput(QThread):
    data_signal = Signal(dict)
    status_signal = Signal(str)

    def __init__(self, port='', baudrate=57600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.eeg = None
        self.auto_scan = True # Modificado para True para descobrir o Brainlink
        self.last_emit = 0

    def _on_data(self, data: BrainLinkData):
        """Callback para receber dados do parser e emitir sinal Qt"""
        now = time.time()
        # Rate-limiting: Emite apenas 4 vezes por segundo
        if now - self.last_emit < 0.25:
            return
            
        self.last_emit = now
        
        # Debug log para o EEG apenas de vez em quando
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
                    # Removido: fallback para TODAS as portas do sistema, que causava lentidão extrema

        for port in ports_to_try:
            try:
                print(f"[DEBUG EEG_INPUT] Iniciando tentativa na porta: {port}")
                self.status_signal.emit(f"Tentando EEG em {port}...")
                self.eeg = BrainLinkEEG(port=port, baudrate=self.baudrate)
                
                print(f"[DEBUG EEG_INPUT] Chamando connect() para {port}...")
                sucesso = self.eeg.connect()
                
                if sucesso:
                    # Validar se realmente recebemos dados (Evitar portas Bluetooth "Incoming" mortas)
                    print(f"[DEBUG EEG_INPUT] A porta {port} conectou! Verificando se o dispositivo envia fluxo de dados (timeout 2.5s)...")
                    dados_recebidos = False
                    start_time = time.time()
                    
                    while time.time() - start_time < 1.5: # Reduzido de 2.5s para 1.5s
                        try:
                            if self.eeg.serial and self.eeg.serial.in_waiting > 0:
                                dados_recebidos = True
                                print(f"[DEBUG EEG_INPUT] Bytes detectados na linha! ({self.eeg.serial.in_waiting} bytes)")
                                break
                        except Exception as e:
                            print(f"[DEBUG EEG_INPUT] Porta caiu inexperadamente durante verificação (Falso Positivo Crash): {e}")
                            break
                        time.sleep(0.1)
                        
                    if not dados_recebidos:
                        print(f"[DEBUG EEG_INPUT] FALSO POSITIVO: A porta {port} abriu, mas a tiara não enviou nenhum byte. Provavelmente é uma porta Bluetooth Incoming errada. Tentando a próxima...")
                        self.eeg.disconnect()
                        continue
                        
                    self.eeg.add_callback(self._on_data)
                    self.port = port
                    self.status_signal.emit(f"BrainLink conectado ({port})")
                    print(f"[DEBUG EEG_INPUT] SUCCESSO DEFINITIVO! BrainLink detectado e enviando dados na porta {port}")
                    self.running = True
                    break
                else:
                    print(f"[DEBUG EEG_INPUT] Falha na resposta do connect() para a porta {port}. Tentando a próxima...")

            except Exception as e:
                print(f"[DEBUG EEG_INPUT] EXCEÇÃO inesperada ao tentar porta {port}: {str(e)}")
                continue
        
        if self.running:
            last_debug = time.time()
            bytes_read_total = 0
            while self.running:
                if self.eeg and self.eeg.serial and self.eeg.serial.is_open:
                    if self.eeg.serial.in_waiting > 0:
                        bytes_read_total += self.eeg.serial.in_waiting
                        
                self.eeg.read_once() 
                time.sleep(0.01)
                
                if time.time() - last_debug > 2.0:
                    if bytes_read_total == 0:
                        print(f"[DEBUG EEG_INPUT] ALERTA: Conexão mantida na porta {self.port}, mas o fluxo de dados do bluetooth parou!")
                    else:
                        pass # Silenciado quando ocorrendo corretamente
                    bytes_read_total = 0
                    last_debug = time.time()
        else:
            self.status_signal.emit("Falha ao encontrar BrainLink.")
            self.stop()

    def stop(self):
        self.running = False
        if self.eeg:
            self.eeg.disconnect()
        self.status_signal.emit("EEG desconectado")
        self.quit()
