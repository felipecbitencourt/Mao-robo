import inspect
import time
from PySide6.QtCore import QObject, Signal

from PySide6.QtCore import QObject, Signal, QThread

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
            
        self.output_obj.status_signal.emit("Iniciando sequência de teste...")
        pins = self.output_obj.pins # [10, 9, 8, 7, 6]
        
        # Abre todos
        for pin in pins:
            self.output_obj.board.digital[pin].write(0)
        time.sleep(1)
        
        # Testa um por um como no script testar-dedos.py
        test_values = [150, 180, 180, 180, 130] # Valores para cada pino
        for i, pin in enumerate(pins):
            self.output_obj.board.digital[pin].write(test_values[i])
            time.sleep(1)
            self.output_obj.board.digital[pin].write(0)
            time.sleep(1)
            
        self.output_obj.status_signal.emit("Teste de servos finalizado")

class ArduinoOutput(QObject):
    status_signal = Signal(str)

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

    def connect(self):
        """Tenta conectar ao Arduino via pyfirmata"""
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"DEBUG ARDUINO: Portas detectadas no sistema: {ports}")

        try:
            print(f"DEBUG ARDUINO: Tentando abrir {self.port}...")
            self.status_signal.emit(f"Tentando abrir porta {self.port}...")
            self.board = Arduino(self.port)
            
            print("DEBUG ARDUINO: Portas aberta. Configurando pinos...")
            # Configura pinos como SERVO
            for pin in self.pins:
                self.board.digital[pin].mode = SERVO
            
            print(f"DEBUG ARDUINO: Sucesso! Hardware pronto na {self.port}")
            self.status_signal.emit(f"Hardware conectado na {self.port}")
            return True
        except Exception as e:
            msg = f"DEBUG ARDUINO: ERRO na conexão: {str(e)}"
            print(msg)
            self.status_signal.emit(f"Falha na conexão. Verifique o terminal.")
            return False

    def run_test_sequence(self):
        """Dispara a thread de teste"""
        if self.board:
            print("DEBUG ARDUINO: Iniciando worker de teste...")
            self.test_worker = TestThread(self)
            self.test_worker.start()
        else:
            print("DEBUG ARDUINO: Impossível testar - Hardware não conectado.")

    def send_hand_command(self, gesture_id):
        """Envia comando de gesto"""
        if not self.board:
            return
            
        print(f"DEBUG ARDUINO: Enviando Gesto ID {gesture_id} para a mão...")
        """
        Recebe ID do gesto e move os servos da mão.
        Ex: ID 15 (Mão Aberta) -> Todos em 0 graus.
        Ex: ID 0 (Punho Fechado) -> Todos nos valores de fechamento.
        """
        if not self.board or not self.active:
            return

        # Para fins de simplificação neste Hub:
        # Se ID for 15 (Aberta), abre tudo.
        # Se ID for 0 (Fechada), fecha tudo.
        # Para IDs intermediários, podemos fazer lógica de bits se desejar.
        
        if gesture_id == 15: # ABERTA
            for pin in self.pins:
                self.board.digital[pin].write(0)
        elif gesture_id == 0: # FECHADA
            for pin in self.pins:
                val = self.VALORES_FECHADOS.get(pin, 140)
                self.board.digital[pin].write(val)
        
        # Opcional: Para gestos parciais (ex: ID 1, 2, 4, 8), 
        # poderíamos mover dedos específicos usando bits.

    def disconnect(self):
        if self.board:
            self.board.exit()
            self.board = None
            self.status_signal.emit("Arduino desconectado")
