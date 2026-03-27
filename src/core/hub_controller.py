import time
from PySide6.QtCore import QObject, Signal, QThread
import os
from inputs.camera_input import CameraInput
from inputs.glove_input import GloveInput
from inputs.eeg_input import EEGInput
from processing.hand_processor import HandProcessor
from outputs.arduino_output import ArduinoOutput
from core.config_manager import ConfigManager

class HubController(QObject):
    prediction_signal = Signal(dict)
    status_signal = Signal(str)
    frame_signal = Signal(object, int)  # Frame, SourceID (0=Main, 1=Dual)
    glove_signal = Signal(dict)   # Sinal para os dados de EEG (muda para EEG na verdade, mas o sinal é unificado)
    eeg_signal = Signal(dict)     # Sinal específico para telemetria EEG
    discovery_finished_signal = Signal(bool)
    arduino_status_signal = Signal(bool)
    fps_signal = Signal(float)

    def __init__(self):
        super().__init__()
        self.running = False
        self.camera = None
        self.camera2 = None
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
        self.eeg_gain = self.config.get("eeg_gain", 1.0)
        self.eeg_smoothing = self.config.get("eeg_smoothing", 0.7)
        self._ema_state = {}
        
        # Estado Global de Predição
        self._last_valid_prediction = {"gesture_id": -1, "timestamp": 0, "source": "NONE"}
        
        # Calibração e Classificação
        self.calibration_state = None
        self.calibration_buffer = []
        self.calibrated_vectors = self.config.get("glove_calibration", {})
        self.glove_weights = self.config.get("glove_weights", [1.0, 1.0, 1.0, 1.0, 1.0])
        
        # Clinical Calibration
        self.clinical_calibration_active = False
        self.clinical_stage = None
        self.clinical_max_buffer = []
        self.clinical_min_buffer = []
        self.current_sample_max = None
        self.current_sample_min = None
        self.clinical_thresholds = self.config.get("glove_clinical_thresholds", [])
        
        # Dual Vision State
        self.camera_index = self.config.get("camera_index", 0)
        self.camera2_index = self.config.get("camera2_index", 1)
        self.dual_vision_active = False
        
        # Portas detectadas
        self.eeg_port_detected = self.config.get("eeg_port", "")
        self.camera_index = self.config.get("camera_index", 0)
        
        # Conexão: Frames da câmera -> Processador de Mão
        self.processor.prediction_signal.connect(self._handle_camera_prediction)
        self.processor.processed_frame_signal.connect(self.frame_signal.emit)        
        # Conexão status arduino
        self.arduino.status_signal.connect(self.status_signal.emit)
        self.arduino.arduino_status_signal.connect(self.arduino_status_signal.emit)
        
        # Conexão FPS
        self.processor.fps_signal.connect(self.fps_signal.emit)

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

    def set_camera_active(self, active, index=None):
        if index is not None and index != self.camera_index:
            self.camera_index = index
            self.config.set("camera_index", index)
            if self.camera:
                self.camera.stop()
                self.camera = None # Recria no próximo start

        if active:
            if not self.camera:
                self.camera = CameraInput(camera_index=self.camera_index)
                self.camera.frame_signal.connect(lambda f: self.processor.process_frame(f, 0))
            self.camera.start()
            self.processor.start() # Sempre ligar processador se houver câmera
            self.status_signal.emit(f"Câmera 1 ATIVADA (Índice: {self.camera_index})")
        else:
            if self.camera:
                self.camera.stop()
            self.status_signal.emit("Câmera 1 DESATIVADA")

    def set_dual_vision(self, active, index=None):
        """Ativa/Desativa a segunda câmera para visão estéreo"""
        if index is not None and index != self.camera2_index:
            self.camera2_index = index
            self.config.set("camera2_index", index)
            if self.camera2:
                self.camera2.stop()
                self.camera2 = None

        self.dual_vision_active = active
        if active:
            if not self.camera2:
                self.camera2 = CameraInput(camera_index=self.camera2_index)
                self.camera2.frame_signal.connect(lambda f: self.processor.process_frame(f, 1))
            self.camera2.start()
            self.status_signal.emit(f"Visão Dual ATIVADA (Câmera 2 Índice: {self.camera2_index})")
        else:
            if self.camera2:
                self.camera2.stop()
            self.status_signal.emit("Visão Dual DESATIVADA")

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
            # Pega a porta mais atual da configuração (selecionada na UI)
            port = self.config.get("eeg_port", "")
            
            # Se o objeto não existe ou a porta mudou, (re)cria
            if not self.eeg or self.eeg.port != port:
                if self.eeg: 
                    self.eeg.stop()
                    self.eeg.wait()
                
                print(f"DEBUG HUB: Iniciando EEG na porta {port}")
                self.eeg = EEGInput(port=port)
                self.eeg.status_signal.connect(self.status_signal.emit)
                self.eeg.data_signal.connect(self._handle_eeg_data)
            
            self.eeg.start()
            self.status_signal.emit(f"EEG ATIVADO ({port})")
        else:
            if self.eeg:
                self.eeg.stop()
            self.status_signal.emit("EEG DESATIVADO")

    def _handle_camera_prediction(self, data):
        """Processa predição vinda da câmera (simples ou fundida)"""
        if data.get("source") == "FUSION":
            data["source"] = "VISÃO DUAL (FUSÃO)"
        else:
            cam_id = data.get("cam_id", 0)
            data["source"] = f"CAMERA {cam_id + 1}"
            
        self._dispatch_prediction(data)

    def _handle_glove_data(self, data):
        """Processa dados da luva e emite como predição unificada"""
        sensors = data.get("sensors", [])
        
        if self.calibration_state:
            self.calibration_buffer.append(sensors)  # Modificado para pegar todos os sensores
            # Durante calibração, apenas mostramos a telemetria, não mudamos o gesto ainda
            self.glove_signal.emit(data)
            return

        # Logica de Calibração Clínica em Tempo Real
        if self.clinical_calibration_active:
            if self.clinical_stage == 'OPEN':
                if self.current_sample_max is None:
                    self.current_sample_max = sensors[:]
                else:
                    self.current_sample_max = [max(a, b) for a, b in zip(self.current_sample_max, sensors)]
            elif self.clinical_stage == 'CLOSED':
                if self.current_sample_min is None:
                    self.current_sample_min = sensors[:]
                else:
                    self.current_sample_min = [min(a, b) for a, b in zip(self.current_sample_min, sensors)]
            
            self.glove_signal.emit(data)
            return

        gid = data.get("gesture_id", -1)
        fingers_data = None
        
        # Mapeamento Dinâmico Fluido direto dos sensores nativos para ângulos do Arduino!
        if len(sensors) >= 5:
            # Se tivermos calibração clínica (18 thresholds), usamos para normalizar os 5 principais
            if len(self.clinical_thresholds) >= 5:
                # Normalização Binária/Suave baseada no threshold clínico
                # Se acima do threshold (FECHADO), se abaixo (ABERTO)
                # Para o motor, 1.0 é aberto, 0.0 é fechado. 
                # sensors[i] >= threshold -> fechado (0.0)
                # sensors[i] < threshold -> aberto (1.0)
                s0 = 0.0 if sensors[0] >= self.clinical_thresholds[0] else 1.0
                s1 = 0.0 if sensors[1] >= self.clinical_thresholds[1] else 1.0
                s2 = 0.0 if sensors[2] >= self.clinical_thresholds[2] else 1.0
                s3 = 0.0 if sensors[3] >= self.clinical_thresholds[3] else 1.0
                s4 = 0.0 if sensors[4] >= self.clinical_thresholds[4] else 1.0
            else:
                # Multiplicador Dinâmico Sensível (fallback)
                s0 = max(0.0, min(1.0, sensors[0] * self.glove_weights[0]))
                s1 = max(0.0, min(1.0, sensors[1] * self.glove_weights[1]))
                s2 = max(0.0, min(1.0, sensors[2] * self.glove_weights[2]))
                s3 = max(0.0, min(1.0, sensors[3] * self.glove_weights[3]))
                s4 = max(0.0, min(1.0, sensors[4] * self.glove_weights[4]))
            
            # Inversão Físico-Robótica: 1.0 da luva (Aberto) mapeia para 60º na Garra

            # 0.0 da luva (Fechado) mapeia para 180º ou 100% no Polegar
            fingers_data = {
                'polegar': (1.0 - s0) * 100.0,
                'indicador': 180 - (s1 * 120),
                'medio': 180 - (s2 * 120),
                'anelar': 180 - (s3 * 120),
                'minimo': 180 - (s4 * 120)
            }
        
        # Se tivermos calibração, tratamos de forma contínua ou por distância
        if self.calibrated_vectors:
            gid = self._classify_by_distance(sensors)
        else:
            if gid == -1: gid = 15 # Valor default genérico se não calibrado

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
            20: "BEM FECHADA",
            21: "MEIO ABERTA",
            22: "BEM ABERTA"
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

    def start_clinical_step(self, stage):
        """Inicia a captura para um passo de calibração clínica (OPEN ou CLOSED)"""
        print(f"DEBUG HUB: Iniciando captura clínica - ESTÁGIO: {stage}")
        self.clinical_stage = stage
        self.clinical_calibration_active = True
        self.current_sample_max = None
        self.current_sample_min = None

    def stop_clinical_step(self):
        """Finaliza a captura do estágio atual e armazena os extremos se for o caso"""
        if self.clinical_stage == 'OPEN' and self.current_sample_max:
            self.clinical_max_buffer.append(self.current_sample_max)
        elif self.clinical_stage == 'CLOSED' and self.current_sample_min:
            self.clinical_min_buffer.append(self.current_sample_min)
        
        self.clinical_calibration_active = False
        self.clinical_stage = None

    def calculate_clinical_final(self):
        """Calcula a média dos limites e gera os thresholds finais"""
        if not self.clinical_max_buffer or not self.clinical_min_buffer:
            return False
            
        import numpy as np
        # Média dos máximos capturados no estágio OPEN
        avg_max = np.mean(self.clinical_max_buffer, axis=0)
        # Média dos mínimos capturados no estágio CLOSED
        avg_min = np.mean(self.clinical_min_buffer, axis=0)
        
        # Threshold é o ponto médio (mesma lógica do script felipe_realtime)
        self.clinical_thresholds = ((avg_max + avg_min) / 2.0).tolist()
        
        self.config.set("glove_clinical_thresholds", self.clinical_thresholds)
        print(f"DEBUG HUB: Calibração Clínica concluída. {len(self.clinical_thresholds)} thresholds salvos.")
        
        # Limpa buffers
        self.clinical_max_buffer = []
        self.clinical_min_buffer = []
        return True

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
        # Aplica amplificador de sensibilidade: expande variações em torno do ponto médio (50)
        gain = getattr(self, 'eeg_gain', 1.0)
        raw_att = data.get("attention", 0)
        raw_med = data.get("meditation", 0)
        
        amp_att = int(max(0, min(100, 50 + (raw_att - 50) * gain)))
        amp_med = int(max(0, min(100, 50 + (raw_med - 50) * gain)))
        
        # Substitui os valores no dict com os amplificados
        data["attention"] = amp_att
        data["meditation"] = amp_med
        data["raw_attention"] = raw_att  # Preserva original para debug
        data["raw_meditation"] = raw_med
        
        # Calcula métricas customizadas a partir das 8 bandas brutas
        waves = data.get("waves", {})
        low_alpha = waves.get("low_alpha", 0)
        high_alpha = waves.get("high_alpha", 0)
        low_beta = waves.get("low_beta", 0)
        high_beta = waves.get("high_beta", 0)
        theta = waves.get("theta", 0)
        
        alpha_sum = low_alpha + high_alpha
        beta_sum = low_beta + high_beta
        
        # Métricas customizadas brutas (divisão segura)
        raw_metrics = {
            "foco_real": min(100, (beta_sum / max(1, alpha_sum)) * 25),
            "relaxamento_real": min(100, (alpha_sum / max(1, beta_sum)) * 25),
            "sonolencia": min(100, (theta / max(1, low_alpha)) * 25),
            "engajamento": min(100, (beta_sum / max(1, alpha_sum + theta)) * 25),
        }
        
        # Aplica filtro EMA (Exponential Moving Average) para suavizar espasmos
        s = getattr(self, 'eeg_smoothing', 0.7)
        smoothed = {}
        for key, raw_val in raw_metrics.items():
            prev = self._ema_state.get(key, raw_val)
            smoothed[key] = prev * s + raw_val * (1.0 - s)
            self._ema_state[key] = smoothed[key]
        
        data["custom_metrics"] = smoothed
        
        self.eeg_signal.emit(data)
        
        # Controle sequencial de dedos pelo EEG
        if getattr(self, "eeg_control_mode", "none") != "none":
            mode = self.eeg_control_mode
            
            # Pega o valor (seja NeuroSky ou Custom)
            if mode in ["foco_real", "relaxamento_real", "sonolencia", "engajamento"]:
                val = data.get("custom_metrics", {}).get(mode, 0)
            else:
                val = data.get(mode, 0)
            
            # Apenas envia predição se a confiança (signal) for boa
            sig = data.get("signal", 200)
            if sig < 50:
                # Modos customizados costumam ser proporcionais
                if mode == "foco_real":
                    # Foco real: quanto maior, mais aberta a mão (0=fechado, 100=aberto)
                    fingers_data = {k: val for k in ['polegar', 'indicador', 'medio', 'anelar', 'minimo']}
                    # Ajuste de escala para os servos (0-100 -> angulos)
                    # No polegar 0=fechado(50), 100=aberto(130) -> 50 + val*0.8
                    # Nos outros 0=fechado(60), 100=aberto(180) -> 60 + val*1.2
                    fingers_data['polegar'] = 50 + (val * 0.8)
                    for k in ['indicador', 'medio', 'anelar', 'minimo']:
                        fingers_data[k] = 60 + (val * 1.2)
                else:
                    # Meditação abre a mão (0=fechado, 100=aberto)
                    # Atenção fecha a mão (0=aberto, 100=fechado)
                    invert = (mode == 'attention')
                    fingers_data = self._calculate_eeg_fingers(val, invert=invert)
                
                prediction_data = {
                    "prediction": f"EEG {mode.upper()}: {int(val)}%",
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
                # Bypass completo no Debouncer de repetidor se houver movimento FLUIDO ('fingers')
                if "fingers" in data:
                    self._last_valid_prediction = data
                    should_emit = True
                else:
                    last_gid = self._last_valid_prediction.get("gesture_id")
                    last_src = self._last_valid_prediction.get("source")
                    if gid != last_gid or source != last_src or (now - self._last_valid_prediction.get("timestamp", 0) > 0.4):
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
        """Varre o sistema em busca de Arduino e BrainLink (Sincrono para evitar race conditions)"""
        self.status_signal.emit("Auto-detectando dispositivos...")
        
        # 1. Arduino
        success_arduino = self.arduino.connect(auto_scan=True)
        if success_arduino:
            self.config.set("arduino_port", self.arduino.port)
            self.status_signal.emit(f"Arduino na porta {self.arduino.port}")
        
        # 2. EEG
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            p_desc = p.description.lower()
            if "brainlink" in p_desc or "bluetooth" in p_desc or "mindwave" in p_desc:
                self.config.set("eeg_port", p.device)
                self.status_signal.emit(f"Porta EEG detectada: {p.device}")
                break
        
        self.status_signal.emit("Auto-detecção finalizada.")
        self.discovery_finished_signal.emit(True)

    def set_glove_weight(self, index, weight):
        """Ajusta do multiplicador de calibração em tempo de execução"""
        if 0 <= index < 5:
            self.glove_weights[index] = weight
            self.config.set("glove_weights", self.glove_weights)
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
            if self.camera2:
                self.camera2.stop()
                self.camera2.wait()
            if self.glove:
                self.glove.stop()
                self.glove.wait() 
            
            self.processor.stop() # Para processamento
            self.status_signal.emit("Sistema parado")

    def calibrate(self):
        self.status_signal.emit("Iniciando calibração...")
        # Lógica de calibração
        self.status_signal.emit("Calibração finalizada")
