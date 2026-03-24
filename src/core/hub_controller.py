import time
from PySide6.QtCore import QObject, Signal
from inputs.camera_input import CameraInput
from inputs.glove_input import GloveInput
from inputs.eeg_input import EEGInput
from processing.hand_processor import HandProcessor
from outputs.arduino_output import ArduinoOutput
from core.config_manager import ConfigManager

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
        
        # Gerenciador de Configurações Persistentes
        self.config = ConfigManager()
        
        # Conecta no arduino usando a última porta salva na configuração
        port = self.config.get("arduino_port", "COM5")
        self.arduino = ArduinoOutput(port=port)
        
        # Modo de controle do EEG: 'none', 'attention', 'meditation'
        self.eeg_control_mode = 'none'
        
        # Estado Global de Predição para evitar conflitos entre fontes
        self._last_valid_prediction = {"gesture_id": -1, "timestamp": 0, "source": "NONE"}
        
        # Calibração e Classificação Personalizada
        self.calibration_state = None  # None, 'CLOSED', 'HALF', 'OPEN'
        self.calibration_buffer = []
        # Carrega a calibração invisível do disco! Evita recalibrar a luva toda vez que ligar
        self.calibrated_vectors = self.config.get("glove_calibration", {})
        
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
            self.calibration_buffer.append(sensors)  # Modificado para pegar todos os sensores
            # Durante calibração, apenas mostramos a telemetria, não mudamos o gesto ainda
            self.glove_signal.emit(data)
            return

        gid = data.get("gesture_id", -1)
        fingers_data = None
        
        # Se tivermos calibração, tratamos de forma contínua ou por distância
        if self.calibrated_vectors:
            gid = self._classify_by_distance(sensors)
            # Se já calibramos os 3 estados, habilitamos controle fluido!
            if 'CLOSED' in self.calibrated_vectors and 'HALF' in self.calibrated_vectors and 'OPEN' in self.calibrated_vectors:
                fingers_data = self._calculate_fluid_fingers(sensors)

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
        
        if fingers_data:
            prediction_data["fingers"] = fingers_data
            
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
        
        # Persiste a calibração silenciosamente no arquivo JSON
        self.config.set("glove_calibration", self.calibrated_vectors)

    def _calculate_fluid_fingers(self, sensors):
        FINGER_MAP = {
            'polegar': [0, 1, 2],
            'indicador': [3, 4, 5],
            'medio': [6, 7, 8],
            'anelar': [9, 10, 11],
            'minimo': [12, 13, 14]
        }
        
        c_closed = self.calibrated_vectors.get('CLOSED', [])
        c_half = self.calibrated_vectors.get('HALF', [])
        c_open = self.calibrated_vectors.get('OPEN', [])
        
        fingers_out = {}
        for nome_dedo, indices in FINGER_MAP.items():
            perc_list = []
            for idx in indices:
                if idx < len(sensors) and idx < len(c_closed) and idx < len(c_half) and idx < len(c_open):
                    v = sensors[idx]
                    p = self._interpolate_sensor(v, c_closed[idx], c_half[idx], c_open[idx])
                    perc_list.append(p)
            
            if perc_list:
                avg_perc = sum(perc_list) / len(perc_list)
                if nome_dedo == 'polegar':
                    # Mapeia 0.0-1.0 para 50 (fechado) a 130 (aberto)
                    fingers_out[nome_dedo] = 50 + (avg_perc * 80)
                else:
                    # Mapeia 0.0-1.0 para angulo 60 (fechado) a 180 (aberto)
                    fingers_out[nome_dedo] = 60 + (avg_perc * 120)

        return fingers_out

    def _interpolate_sensor(self, value, c_closed, c_half, c_open):
        """Mapeia interpolação em 3 pontos para porcentagem de abertura"""
        if c_closed == c_open: return 0.5
        is_increasing = c_open > c_closed 
        
        if is_increasing:
            if value <= c_closed: return 0.0
            if value >= c_open: return 1.0
            if value <= c_half and c_half != c_closed:
                return 0.0 + 0.5 * (value - c_closed) / (c_half - c_closed)
            elif c_open != c_half:
                return 0.5 + 0.5 * (value - c_half) / (c_open - c_half)
            else: return 0.5
        else:
            if value >= c_closed: return 0.0
            if value <= c_open: return 1.0
            if value >= c_half and c_half != c_closed:
                return 0.0 + 0.5 * (value - c_closed) / (c_half - c_closed)
            elif c_open != c_half:
                return 0.5 + 0.5 * (value - c_half) / (c_open - c_half)
            else: return 0.5

    def _classify_by_distance(self, sensors):
        """Classifica o gesto baseado na menor distância euclidiana para os vetores calibrados"""
        import math
        
        if not self.calibrated_vectors:
            return -1

        best_state = -1
        min_dist = float('inf')
        
        state_to_id = {'CLOSED': 20, 'HALF': 21, 'OPEN': 22}
        
        for state, vector in self.calibrated_vectors.items():
            dim = min(len(sensors), len(vector))
            if dim == 0: continue
            
            dist = math.sqrt(sum((sensors[i] - vector[i]) ** 2 for i in range(dim)))
            if dist < min_dist:
                min_dist = dist
                best_state = state_to_id[state]
        
        # Como o erro global sobre ~15 sensores será maior, usamos uma tolerância alta
        if min_dist < 40.0:
            return best_state
        return best_state # Retorna o mais próximo garantindo uma ID para os dados fluidos

    def _handle_eeg_data(self, data):
        """Processa dados EEG e se o controle estiver ativo, interage com a mão"""
        self.eeg_signal.emit(data)
        
        # Controle sequencial de dedos pelo EEG
        if getattr(self, "eeg_control_mode", "none") != "none":
            mode = self.eeg_control_mode
            val = data.get(mode, 0)
            
            # Apenas envia predição se a confiança (signal) for boa
            sig = data.get("signal", 200)
            if sig < 50:
                # Meditação abre a mão (0=fechado, 100=aberto)
                # Atenção fecha a mão (0=aberto, 100=fechado)
                invert = (mode == 'attention')
                
                fingers_data = self._calculate_eeg_fingers(val, invert=invert)
                prediction_data = {
                    "prediction": f"EEG {mode.upper()}: {val}%",
                    "gesture_id": 30, # ID para designação fluida
                    "confidence": 100 - sig, 
                    "source": "EEG",
                    "timestamp": data.get("timestamp"),
                    "fingers": fingers_data
                }
                self._dispatch_prediction(prediction_data)
        else:
            if data.get("attention", 0) > 80:
                self.status_signal.emit("Foco EEG Elevado!")

    def _calculate_eeg_fingers(self, val, invert=False):
        """Mapeia valor 0-100 para a abertura sequencial dos 5 dedos (20 por dedo)"""
        fingers_out = {}
        # Ordem de abertura
        dedos = ['polegar', 'indicador', 'medio', 'anelar', 'minimo']
        
        for i, nome_dedo in enumerate(dedos):
            start_threshold = i * 20
            end_threshold = (i + 1) * 20
            
            if val <= start_threshold:
                perc = 0.0
            elif val >= end_threshold:
                perc = 1.0
            else:
                perc = (val - start_threshold) / 20.0
            
            # Se invertido, 0 = 1.0 (aberto), 1.0 = 0.0 (fechado)
            if invert:
                perc = 1.0 - perc
                
            if nome_dedo == 'polegar':
                fingers_out[nome_dedo] = 50 + (perc * 80)
            else:
                fingers_out[nome_dedo] = 60 + (perc * 120)
                
        return fingers_out
        
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
                    self.arduino.send_hand_command(gid, fingers_data=data.get("fingers"))
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
