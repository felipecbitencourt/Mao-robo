import inspect
import threading
import time
from PySide6.QtCore import QObject, Signal

from PySide6.QtCore import QObject, Signal, QThread

from core.ports import is_arduino_port_description, is_eeg_port_description

# Fix para pyfirmata em Python 3.13+
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

try:
    from pyfirmata import Arduino, SERVO
except ImportError:
    print("Aviso: pyfirmata não instalado. Controle do Arduino desabilitado.")

class TestThread(QThread):
    def __init__(self, output_obj):
        super().__init__()
        self.output_obj = output_obj

    def run(self):
        if not self.output_obj.board:
            return
            
        out = self.output_obj
        out.status_signal.emit("Iniciando sequência de teste...")
        pins = out.pins # [10, 9, 8, 7, 6]

        def pause(seconds):
            # Dorme em passos curtos para a parada de emergência interromper o teste
            end = time.time() + seconds
            while time.time() < end:
                if out._abort_test.is_set():
                    return False
                time.sleep(0.05)
            return True

        # Abre todos
        for pin in pins:
            out._write(pin, 0)
        if not pause(1):
            return

        # Testa um por um como no script testar-dedos.py
        test_values = [150, 180, 180, 180, 130] # Valores para cada pino
        for i, pin in enumerate(pins):
            out._write(pin, test_values[i])
            if not pause(1):
                return
            out._write(pin, 0)
            if not pause(1):
                return

        out.status_signal.emit("Teste de servos finalizado")

class ArduinoOutput(QObject):
    status_signal = Signal(str)
    arduino_status_signal = Signal(bool)

    def __init__(self, port='COM5'):
        super().__init__()
        self.port = port
        self.board = None
        self.pins = [10, 9, 8, 7, 6] # Polegar, Indicador, Medio, Anelar, Minimo
        self.active = False
        self.test_worker = None
        
        # Valores calibrados para "fechado" de cada dedo (conforme servo_braco3d.py)
        self.VALORES_FECHADOS = {
            10: 150,  # Polegar
            9: 180,   # Indicador
            8: 160,   # Medio
            7: 180,   # Anelar
            6: 130    # Minimo
        }
        
        self.pin_map = {
            'polegar': 10,
            'indicador': 9,
            'medio': 8,
            'anelar': 7,
            'minimo': 6
        }
        
        # Estado atual dos servos para suavização no modo fluido
        self.posicao_atual = {pin: 0 for pin in self.pins}
        # Suavização (lerp) do movimento: opcional, desligada por padrão.
        # Desligada, o servo vai direto para a posição alvo.
        self.suavizar = False
        
        self._available_ports = []

        # Escritas na serial vêm da thread principal e da thread de teste
        self._lock = threading.Lock()
        self._abort_test = threading.Event()

    # Posição segura: mão aberta (mesmo valor usado pelo gesto "MÃO ABERTA")
    SAFE_POSITION = 0

    def _write(self, pin, value):
        board = self.board
        if not board:
            return
        with self._lock:
            board.digital[pin].write(value)

    def safe_stop(self):
        """Parada de emergência: corta o envio, interrompe o teste e leva os
        servos para a posição segura (mão aberta). Funciona mesmo com a saída
        desativada, desde que a placa esteja conectada."""
        self.active = False
        self._abort_test.set()
        if self.test_worker is not None and self.test_worker.isRunning():
            self.test_worker.wait(1000)
        if not self.board:
            return False
        try:
            for pin in self.pins:
                self._write(pin, self.SAFE_POSITION)
                self.posicao_atual[pin] = self.SAFE_POSITION
            self.status_signal.emit("Motores parados (mão aberta)")
            return True
        except Exception as e:
            self.status_signal.emit(f"Falha ao parar motores: {e}")
            return False

    @staticmethod
    def list_available_ports():
        """Retorna lista de descrições das portas COM"""
        import serial.tools.list_ports
        return [f"{p.device} ({p.description})" for p in serial.tools.list_ports.comports()]

    def connect(self, auto_scan=False):
        """Tenta conectar ao Arduino. Se auto_scan for True, tenta todas as portas."""
        if self.board:
            try:
                # Tenta um comando simples para ver se ainda está vivo
                self.board.iterate()
                print("DEBUG ARDUINO: Já conectado e operacional.")
                self.arduino_status_signal.emit(True)
                return True
            except:
                print("DEBUG ARDUINO: Conexão antiga perdida. Reconectando...")
                self.board = None

        import serial.tools.list_ports
        available = serial.tools.list_ports.comports()
        
        ports_to_try = [self.port] if self.port else []
        if auto_scan:
            # Só tenta portas que pareçam Arduino/USB-serial. Abrir o Firmata numa
            # porta Bluetooth (ex.: a tiara EEG) pode travar por vários segundos.
            ports_to_try = []
            for p in available:
                if is_arduino_port_description(p.description):
                    ports_to_try.append(p.device)
            # A porta salva entra por último, se não for claramente Bluetooth
            saved = next((p for p in available if p.device == self.port), None)
            if saved and saved.device not in ports_to_try and not is_eeg_port_description(saved.description):
                ports_to_try.append(saved.device)
        
        for port in ports_to_try:
            try:
                print(f"DEBUG ARDUINO: Tentando abrir {port}...")
                self.status_signal.emit(f"Tentando {port}...")
                self.board = Arduino(port)
                # Configura pinos como SERVO
                for pin in self.pins:
                    self.board.digital[pin].mode = SERVO
                
                self.port = port
                print(f"DEBUG ARDUINO: Sucesso na {port}!")
                self.status_signal.emit(f"Conectado na {port}")
                self.arduino_status_signal.emit(True)
                return True
            except Exception as e:
                print(f"DEBUG ARDUINO: Falha na {port}: {str(e)}")
                continue
        
        self.status_signal.emit("Falha ao encontrar Arduino.")
        self.arduino_status_signal.emit(False)
        return False

    def run_test_sequence(self):
        """Dispara a thread de teste"""
        if self.board:
            print("DEBUG ARDUINO: Iniciando worker de teste...")
            self._abort_test.clear()
            self.test_worker = TestThread(self)
            self.test_worker.start()
        else:
            print("DEBUG ARDUINO: Impossível testar - Hardware não conectado.")

    def mover_servo_suave(self, pino, posicao_alvo):
        """Move o servo para a posição alvo. Com self.suavizar ligado, anda só
        30% do caminho por chamada (lerp), o que deixa o movimento mais lento."""
        if not self.board or not self.active: return
        
        max_pos = self.VALORES_FECHADOS.get(pino, 140)
        posicao_alvo = max(0, min(max_pos, posicao_alvo))
        atual = self.posicao_atual[pino]
        
        if self.suavizar:
            nova_pos = int(round(atual + (posicao_alvo - atual) * 0.3))
            # Perto do alvo anda 1° por vez para não parar 1° antes (arredondamento)
            if nova_pos == atual and abs(posicao_alvo - atual) >= 1:
                nova_pos = atual + (1 if posicao_alvo > atual else -1)
        else:
            nova_pos = int(round(posicao_alvo))
        
        # Move se a diferença for significativa para evitar jitter
        if abs(nova_pos - self.posicao_atual[pino]) >= 1:
            self._write(pino, nova_pos)
            self.posicao_atual[pino] = nova_pos

    def posicao_para_abertura(self, pino, abertura):
        """Abertura 0..1 (0 = fechado, 1 = aberto) para a posição do servo."""
        max_servo = self.VALORES_FECHADOS.get(pino, 140)
        abertura = max(0.0, min(1.0, float(abertura)))
        return max_servo * (1.0 - abertura)

    def send_hand_command(self, gesture_id, opening=None):
        """Envia a abertura de cada dedo (modo fluido) ou um gesto discreto"""
        if not self.board or not self.active:
            return

        # Modo fluido: abertura 0..1 por dedo (ver processing/finger_scale.py)
        if opening:
            for nome_dedo, abertura in opening.items():
                pino = self.pin_map.get(nome_dedo)
                if pino is not None:
                    self.mover_servo_suave(pino, self.posicao_para_abertura(pino, abertura))
            return

        print(f"DEBUG ARDUINO: Enviando Gesto ID {gesture_id} para a mão (Modo Binário)...")

        # Para fins de simplificação neste Hub:
        # Se ID for 15 (Aberta), abre tudo.
        # Se ID for 0 (Fechada), fecha tudo.
        # Para IDs intermediários, podemos fazer lógica de bits se desejar.
        
        if gesture_id in [15, 22]: # ABERTA ou BEM ABERTA
            for pin in self.pins:
                self._write(pin, 0)
        elif gesture_id in [0, 20]: # FECHADA ou BEM FECHADA
            for pin in self.pins:
                val = self.VALORES_FECHADOS.get(pin, 140)
                self._write(pin, val)
        elif gesture_id == 21: # MEIO ABERTA (RELAXADA)
            for pin in self.pins:
                target = self.VALORES_FECHADOS.get(pin, 140)
                self._write(pin, int(target * 0.5)) # Posição intermediária
        
        # Opcional: Para gestos parciais (ex: ID 1, 2, 4, 8), 
        # poderíamos mover dedos específicos usando bits.

    def disconnect(self):
        if self.board:
            with self._lock:
                board, self.board = self.board, None
                board.exit()
            self.status_signal.emit("Arduino desconectado")
