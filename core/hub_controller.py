import time
from PySide6.QtCore import QObject, Signal
from inputs.camera_input import CameraInput
from inputs.glove_input import GloveInput
from inputs.eeg_input import EEGInput
from processing.hand_processor import HandProcessor
from outputs.arduino_output import ArduinoOutput

class HubController(QObject):
    prediction_signal = Signal(dict)
    status_signal = Signal(str)
    frame_signal = Signal(object)  # Sinal para o frame da câmera
    glove_signal = Signal(dict)   # Sinal para os dados da luva
    eeg_signal = Signal(dict)     # Sinal para os dados de EEG

    def __init__(self):
        super().__init__()
        self.running = False
        self.camera = None
        self.glove = None
        self.eeg = None
        self.processor = HandProcessor()
        self.arduino = ArduinoOutput(port='COM5') # Conforme servo_braco3d.py
        
        # Estado Global de Predição para evitar conflitos entre fontes
        self._last_valid_prediction = {"gesture_id": -1, "timestamp": 0, "source": "NONE"}
        
        # Calibração e Classificação Personalizada
        self.calibration_state = None  # None, 'CLOSED', 'HALF', 'OPEN'
        self.calibration_buffer = []
        self.calibrated_vectors = {} # {'CLOSED': [v1,v2...], 'HALF': [...], 'OPEN': [...]}
        
        # Conexão: Frames da câmera -> Processador de Mão
        self.processor.prediction_signal.connect(self._handle_camera_prediction)
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

    def set_camera_active(self, active):
        if active:
            if not self.camera:
                self.camera = CameraInput(camera_index=0)
                self.camera.frame_signal.connect(self.processor.process_frame)
            self.camera.start()
            self.processor.start() # Sempre ligar processador se houver câmera
            self.status_signal.emit("Câmera ATIVADA")
        else:
            if self.camera:
                self.camera.stop()
            self.status_signal.emit("Câmera DESATIVADA")

    def set_glove_active(self, active):
        if active:
            if not self.glove:
                self.glove = GloveInput()
                self.glove.status_signal.connect(self.status_signal.emit)
                self.glove.data_signal.connect(self._handle_glove_data)
            self.glove.start()
            self.status_signal.emit("Luva ATIVADA")
        else:
            if self.glove:
                self.glove.stop()
            self.status_signal.emit("Luva DESATIVADA")

    def set_eeg_active(self, active):
        if active:
            if not self.eeg:
                self.eeg = EEGInput(port='COM5') # Porta padrão para teste
                self.eeg.status_signal.connect(self.status_signal.emit)
                self.eeg.data_signal.connect(self._handle_eeg_data)
            self.eeg.start()
            self.status_signal.emit("EEG ATIVADO")
        else:
            if self.eeg:
                self.eeg.stop()
            self.status_signal.emit("EEG DESATIVADO")

    def _handle_camera_prediction(self, data):
        """Processa predição vinda da câmera"""
        data["source"] = "CAMERA"
        self._dispatch_prediction(data)

    def _handle_glove_data(self, data):
        """Processa dados da luva e emite como predição unificada"""
        sensors = data.get("sensors", [])
        
        if self.calibration_state:
            self.calibration_buffer.append(sensors[:5])
            # Durante calibração, apenas mostramos a telemetria, não mudamos o gesto ainda
            self.glove_signal.emit(data)
            return

        gid = data.get("gesture_id", -1)
        
        # Se tivermos calibração, tentamos classificar por distância
        if self.calibrated_vectors:
            gid = self._classify_by_distance(sensors[:5])

        # Mapeamento expandido conforme logs da luva e câmera
        names = {
            15: "MÃO ABERTA",
            0: "PUNHO FECHADO",
            1: "POLEGAR",
            2: "INDICADOR",
            4: "MÉDIO", 
            6: "ANELAR",
            7: "MÍNIMO",
            11: "OK / GESTO 11",
            20: "BEM FECHADA",  # IDs customizados para calibração
            21: "MEIO ABERTA",
            22: "BEM ABERTA",
            -1: "SEM DISPOSITIVO"
        }
        
        prediction_data = {
            "prediction": names.get(gid, f"GESTO {gid}"),
            "gesture_id": gid,
            "confidence": 100, 
            "sensors": sensors,
            "source": "GLOVE",
            "timestamp": data.get("timestamp")
        }
        self.glove_signal.emit(data) # Mantém sinal original para telemetria
        self._dispatch_prediction(prediction_data)

    def start_glove_calibration(self, state):
        """Prepara o Hub para coletar dados de um estado específico"""
        print(f"DEBUG HUB: Coletando dados para estado {state}")
        self.calibration_state = state
        self.calibration_buffer = []

    def finish_glove_calibration_step(self):
        """Calcula a média do estado atual e salva"""
        if not self.calibration_buffer:
            self.calibration_state = None
            return

        import numpy as np
        mean_vector = np.mean(self.calibration_buffer, axis=0).tolist()
        self.calibrated_vectors[self.calibration_state] = mean_vector
        print(f"DEBUG HUB: Estado {self.calibration_state} calibrado: {mean_vector}")
        self.calibration_state = None

    def _classify_by_distance(self, sensors):
        """Classifica o gesto baseado na menor distância euclidiana para os vetores calibrados"""
        import math
        
        if not self.calibrated_vectors:
            return -1

        best_state = -1
        min_dist = float('inf')
        
        state_to_id = {'CLOSED': 20, 'HALF': 21, 'OPEN': 22}
        
        for state, vector in self.calibrated_vectors.items():
            # Distância Euclidiana simplificada
            dist = math.sqrt(sum((s - v) ** 2 for s, v in zip(sensors, vector)))
            if dist < min_dist:
                min_dist = dist
                best_state = state_to_id[state]
        
        # Só aceita se a distância for "razoável" (ajustável)
        if min_dist < 0.5:
            return best_state
        return -1

    def _handle_eeg_data(self, data):
        """Processa dados EEG"""
        # EEG geralmente não gera "gesto" diretamente sem classificador extra
        # Mas podemos emitir status de foco
        self.eeg_signal.emit(data)
        if data.get("attention", 0) > 80:
            self.status_signal.emit("Foco EEG Elevado!")

    def _dispatch_prediction(self, data):
        """Repassa a predição para a UI e para o Arduino com lógica de prioridade"""
        try:
            gid = data.get("gesture_id", -1)
            source = data.get("source", "UNKNOWN")
            now = time.time()
            
            # Garante que temos um timestamp válido para cálculos
            if data.get("timestamp") is None:
                data["timestamp"] = now

            # Lógica de Prioridade:
            # Se recebemos um gesto VÁLIDO (gid != -1), ele sempre tem precedência.
            # Se recebemos um gesto INVÁLIDO (-1), só aceitamos se não houver um gesto válido recente de OUTRA fonte.
            
            should_emit = False
            if gid != -1:
                self._last_valid_prediction = data
                should_emit = True
            else:
                last_ts = self._last_valid_prediction.get("timestamp", 0)
                last_src = self._last_valid_prediction.get("source", "NONE")
                
                if (now - last_ts > 0.5) or (last_src == source):
                    should_emit = True
                    self._last_valid_prediction = data # Atualiza timestamp do "vazio"
            
            if should_emit:
                # Log extremamente visível para debug
                print(f">>> HUB DISPATCH: {source} -> '{data.get('prediction')}' (ID: {gid})")
                self.prediction_signal.emit(data)
                
                # Controle do Arduino
                if self.arduino.active and gid != -1:
                    self.arduino.send_hand_command(gid)
        except Exception as e:
            print(f"!!! ERRO NO DISPATCH: {str(e)}")
            import traceback
            traceback.print_exc()

    def auto_detect_all_ports(self):
        """Varre o sistema em busca de Arduino e BrainLink"""
        self.status_signal.emit("Auto-detectando dispositivos...")
        
        # 1. Arduino
        success_arduino = self.arduino.connect(auto_scan=True)
        
        # 2. EEG (apenas prepara a porta se encontrar algo)
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            if "bluetooth" in p.description.lower() or "brainlink" in p.description.lower():
                if self.eeg:
                    self.eeg.port = p.device
                    self.status_signal.emit(f"Porta EEG ajustada para {p.device}")
                break
        
        if success_arduino:
            self.status_signal.emit("Auto-detecção finalizada com sucesso.")
        else:
            self.status_signal.emit("Auto-detecção completa (verifique Arduino).")


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
