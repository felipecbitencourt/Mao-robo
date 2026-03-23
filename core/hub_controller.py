from PySide6.QtCore import QObject, Signal
from inputs.camera_input import CameraInput
from inputs.glove_input import GloveInput
from processing.hand_processor import HandProcessor
from outputs.arduino_output import ArduinoOutput

class HubController(QObject):
    prediction_signal = Signal(dict)
    status_signal = Signal(str)
    frame_signal = Signal(object)  # Sinal para o frame da câmera
    glove_signal = Signal(dict)   # Sinal para os dados da luva

    def __init__(self):
        super().__init__()
        self.running = False
        self.camera = None
        self.glove = None
        self.processor = HandProcessor()
        self.arduino = ArduinoOutput(port='COM5') # Conforme servo_braco3d.py
        
        # Conexão: Frames da câmera -> Processador de Mão
        self.processor.prediction_signal.connect(self._handle_prediction)
        self.processor.processed_frame_signal.connect(self.frame_signal.emit) 
        
        # Conexão status arduino
        self.arduino.status_signal.connect(self.status_signal.emit)

    def set_hand_output(self, active):
        """Ativa ou desativa o envio de comandos para o Arduino"""
        self.arduino.active = active
        if active:
            print(f"DEBUG HUB: Ativando saída robótica...")
            if not self.arduino.board:
                self.arduino.connect()
            self.status_signal.emit("Saída Robótica ATIVADA")
        else:
            print("DEBUG HUB: Desativando saída robótica.")
            self.status_signal.emit("Saída Robótica DESATIVADA")

    def test_arduino_hand(self):
        """Aciona a sequência de teste de servos no hardware"""
        if self.arduino:
            self.arduino.run_test_sequence()

    def _handle_prediction(self, data):
        """Filtra e repassa a predição para a UI e para o Arduino"""
        self.prediction_signal.emit(data)
        
        # Se a saída estiver ligada e houver predição válida, envia pro Arduino
        if self.arduino.active:
            gid = data.get("gesture_id", -1)
            if gid != -1:
                print(f"DEBUG HUB: Enviando comando {gid} para Arduino...")
                self.arduino.send_hand_command(gid)
            else:
                print("DEBUG HUB: Ignorando comando (Gesto inválido)")
        else:
            # print("DEBUG HUB: Saída inativa. Ignorando predição.")
            pass

    def connect_devices(self, config=None):
        """Inicializa conexões com os dispositivos selecionados"""
        self.status_signal.emit("Conectando dispositivos...")
        
        # Conecta a primeira câmera por padrão
        if not self.camera:
            self.camera = CameraInput(camera_index=0)
            # Conectamos a câmera apenas ao processador, não direto à UI
            self.camera.frame_signal.connect(self.processor.process_frame)
            self.status_signal.emit("Câmera inicializada")

        # Conecta a luva
        if not self.glove:
            self.glove = GloveInput()
            self.glove.status_signal.connect(self.status_signal.emit)
            self.glove.data_signal.connect(self.glove_signal.emit)
            self.status_signal.emit("Luva inicializada")
        
        return True

    def start(self):
        if not self.running:
            self.running = True
            if self.camera:
                self.camera.start()
            if self.glove:
                self.glove.start()
                
            self.processor.start() # Inicia processamento MediaPipe
            self.status_signal.emit("Sistema iniciado")

    def stop(self):
        if self.running:
            self.running = False
            
            if self.camera:
                self.camera.stop()
                self.camera.wait() 
            if self.glove:
                self.glove.stop()
                self.glove.wait() 
            
            self.processor.stop() # Para processamento
            self.status_signal.emit("Sistema parado")

    def calibrate(self):
        self.status_signal.emit("Iniciando calibração...")
        # Lógica de calibração
        self.status_signal.emit("Calibração finalizada")
