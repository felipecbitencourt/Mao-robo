import mediapipe as mp
import cv2
import numpy as np
import time
import os
import threading
from PySide6.QtCore import QObject, QThread, Signal

from core.paths import resource_path

class KalmanFilter:
    """Filtro de Kalman 1D para suavização de sinais (ângulos de servos)"""
    def __init__(self, q=0.1, r=1.0, e=1.0, initial_value=180.0):
        self.q = q      # Process variance (confiança no modelo)
        self.r = r      # Measurement variance (confiança no sensor)
        self.p = e      # Estimated error
        self.x = initial_value # Valor estimado

    def update(self, measurement):
        # Prediction
        self.p = self.p + self.q
        
        # Measurement update
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurement - self.x)
        self.p = (1 - k) * self.p
        
        return self.x

class HandProcessor(QThread):
    prediction_signal = Signal(dict)
    processed_frame_signal = Signal(object, int) # Envia frame com pontos e ID da fonte
    fps_signal = Signal(float)

    def __init__(self, model_path="models/hand_landmarker.task"):
        super().__init__()
        # Último frame pendente de cada câmera (descarta frames velhos sem
        # deixar uma câmera monopolizar o processamento na visão dual)
        self._pending = {}
        self._pending_lock = threading.Lock()
        # Um detector MediaPipe por câmera: no modo VIDEO o detector rastreia a
        # mão entre frames consecutivos, então não pode receber frames de duas
        # câmeras intercalados. Cada um também precisa de timestamps crescentes.
        self._detectors = {}
        self._last_ts = {}
        self.running = False
        self.model_path = resource_path(model_path)
        self._fps_buffer = [] # Buffer para cálculo de FPS
        self._last_fps_emit = 0
        
        # Configuração MediaPipe Tasks (Idêntico ao main_fluido_v2.py)
        self.BaseOptions = mp.tasks.BaseOptions
        self.HandLandmarker = mp.tasks.vision.HandLandmarker
        self.HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        self.VisionRunningMode = mp.tasks.vision.RunningMode
        
        self.latest_predictions = {} # Memória de cada câmera {cam_id: prediction_data}
        
        # Filtros de Kalman para cada dedo (Q=0.2 para agilidade, R=5.0 para filtragem de ruído)
        self.kalman_filters = {
            'polegar': KalmanFilter(q=0.2, r=5.0, initial_value=100.0), # Ratio * 100
            'indicador': KalmanFilter(q=0.2, r=5.0, initial_value=180.0),
            'medio': KalmanFilter(q=0.2, r=5.0, initial_value=180.0),
            'anelar': KalmanFilter(q=0.2, r=5.0, initial_value=180.0),
            'minimo': KalmanFilter(q=0.2, r=5.0, initial_value=180.0),
        }
        
        # Mapeamento de dedos conforme main_fluido_v2.pyne
        
        # Índices para cada dedo conforme main_fluido_v2
        self.INDICES_DEDOS = {
            'indicador': {'mcp': (0, 5, 6), 'pip': (5, 6, 7), 'bit': 0},
            'medio':     {'mcp': (0, 9, 10), 'pip': (9, 10, 11), 'bit': 1},
            'anelar':    {'mcp': (0, 13, 14), 'pip': (13, 14, 15), 'bit': 2},
            'minimo':    {'mcp': (0, 17, 18), 'pip': (17, 18, 19), 'bit': 3}
        }

    def process_frame(self, frame, source_id=0):
        """Guarda o frame mais recente de cada câmera para processamento"""
        with self._pending_lock:
            self._pending[source_id] = frame

    def _create_detector(self):
        options = self.HandLandmarkerOptions(
            base_options=self.BaseOptions(model_asset_buffer=self._model_buffer),
            running_mode=self.VisionRunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return self.HandLandmarker.create_from_options(options)

    def _detector_for(self, source_id):
        det = self._detectors.get(source_id)
        if det is None:
            det = self._create_detector()
            self._detectors[source_id] = det
        return det

    def _next_timestamp(self, source_id):
        """Timestamp em ms estritamente crescente por câmera (exigido pelo modo VIDEO)"""
        ts = int(time.time() * 1000)
        last = self._last_ts.get(source_id, -1)
        if ts <= last:
            ts = last + 1
        self._last_ts[source_id] = ts
        return ts

    def run(self):
        # Carrega o modelo como buffer para evitar problemas com caracteres especiais no caminho (ex: "Códigos")
        with open(self.model_path, 'rb') as f:
            self._model_buffer = f.read()

        with self._pending_lock:
            self._pending.clear()

        self.running = True
        while self.running:
            with self._pending_lock:
                batch = list(self._pending.items())
                self._pending.clear()

            if not batch:
                time.sleep(0.005)
                continue

            for source_id, frame in batch:
                if not self.running:
                    break
                try:
                    prediction_data = None
                    processed_frame = frame

                    try:
                        detector = self._detector_for(source_id)
                        prediction_data, processed_frame = self._analyze_frame(frame, detector, source_id)
                    except Exception as e:
                        print(f"DEBUG ANALYSIS ERROR: {e}")

                    if not self.running:
                        break

                    # Emite o frame processado (SEMPRE)
                    self.processed_frame_signal.emit(processed_frame, source_id)

                    # Salva na memória e funde resultados se a análise teve sucesso
                    if prediction_data:
                        prediction_data["cam_id"] = source_id
                        self.latest_predictions[source_id] = prediction_data

                        fused_data = self._fuse_predictions()
                        if fused_data:
                            self.prediction_signal.emit(fused_data)
                except RuntimeError:
                    # Ocorre quando o MediaPipe fecha o pool antes do loop terminar
                    self.running = False
                    break
                except Exception as e:
                    print(f"DEBUG LOOP ERROR: {e}")

        for det in self._detectors.values():
            try:
                det.close()
            except Exception:
                pass
        self._detectors.clear()
        self._last_ts.clear()
        self.latest_predictions.clear()

    def stop(self):
        self.running = False
        self.wait()

    def _analyze_frame(self, frame, detector, source_id=0):
        """Analisa frame e desenha pontos como no main_fluido_v2.py"""
        if frame is None or detector is None:
            return None, frame
        
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = self._next_timestamp(source_id)

        result = detector.detect_for_video(mp_image, timestamp_ms)
        
        # Cálculo de FPS
        now = time.time()
        self._fps_buffer.append(now)
        if len(self._fps_buffer) > 10:
            self._fps_buffer.pop(0)
            
        if now - self._last_fps_emit > 0.5: # Emitir a cada 500ms
            if len(self._fps_buffer) > 1:
                fps = (len(self._fps_buffer) - 1) / (self._fps_buffer[-1] - self._fps_buffer[0])
                self.fps_signal.emit(fps)
                self._last_fps_emit = now
        
        gesture_id = 0
        confidence = 0
        if result.handedness:
            confidence = int(result.handedness[0][0].score * 100)
            
        fingers_state = {}
        processed_frame = frame.copy()

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            coords = [[lm.x * w, lm.y * h] for lm in landmarks]
            
            # --- Desenhar Pontos (Landmarks) manual conforme main_fluido_v2.py ---
            for i, (cx, cy) in enumerate(coords):
                cor = (0, 255, 0) if i in [5, 6, 9, 10, 13, 14, 17, 18] else (0, 165, 255) # Verde/Laranja
                cv2.circle(processed_frame, (int(cx), int(cy)), 5, cor, -1)

            # --- Dedos (Indicador ao Mínimo) ---
            for nome, info in self.INDICES_DEDOS.items():
                ang_mcp = self.calcular_angulo(coords[info['mcp'][0]], coords[info['mcp'][1]], coords[info['mcp'][2]])
                ang_pip = self.calcular_angulo(coords[info['pip'][0]], coords[info['pip'][1]], coords[info['pip'][2]])
                
                avg_angle = ang_mcp * 0.3 + ang_pip * 0.7
                
                # Se o ângulo for MAIOR que 125 (Dedo Levantado/Aberto), ativamos o bit
                if avg_angle > 125:
                    gesture_id += (2 ** info['bit'])
                
                fingers_state[nome] = int(avg_angle)

            # --- Polegar ---
            p0, p5, p4, p17 = np.array(coords[0]), np.array(coords[5]), np.array(coords[4]), np.array(coords[17])
            palma = np.linalg.norm(p5 - p0)
            dist_polegar = np.linalg.norm(p17 - p4)
            ratio = dist_polegar / palma if palma > 0 else 1
            if ratio > 0.6: # Polegar levantado/aberto
                gesture_id += 16 # Opcional: Bit 4 para polegar se as imagens suportarem
            
            fingers_state['polegar'] = int(ratio * 100)
            confidence = 98
        else:
            gesture_id = -1
        
        # O ID deve ser limitado a 0-15 se o polegar não for usado nas imagens
        display_id = gesture_id % 16 if gesture_id >= 0 else -1
        
        # Retornar dados para o loop principal emitir
        prediction = {
            "prediction": self._get_gesture_name(display_id),
            "gesture_id": display_id,
            "confidence": confidence,
            "fingers": fingers_state,
            "timestamp": time.time()
        }
        
        return prediction, processed_frame

    def calcular_angulo(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        if angle > 180.0: angle = 360 - angle
        return angle

    def _get_gesture_name(self, gid):
        if gid == -1: return "SEM MÃO"
        # Mapeamento para imagens 0-15
        if gid == 15: return "MÃO ABERTA"
        if gid == 0: return "PUNHO FECHADO"
        return f"GESTO {gid}"

    def _fuse_predictions(self):
        """Funde predições de múltiplas câmeras em uma única estável"""
        if not self.latest_predictions:
            return None
            
        # Limpar predições muito antigas (> 200ms) para evitar fantasmas
        now = time.time()
        active_sources = [sid for sid, data in self.latest_predictions.items() if now - data["timestamp"] < 0.2]
        
        if not active_sources:
            return {
                "prediction": "SEM MÃO",
                "gesture_id": -1,
                "confidence": 0,
                "fingers": {},
                "source": "CAMERA",
                "timestamp": now
            }
            
        # Só um canal ativo: repassa a predição dessa câmera (não é fusão)
        if len(active_sources) == 1:
            single = self.latest_predictions[active_sources[0]].copy()
            single["source"] = "CAMERA"
            return single

        # Fusão Multi-Câmera (Lógica: Média Ponderada Bayesiana)
        fused_fingers = {}
        target_keys = ["polegar", "indicador", "medio", "anelar", "minimo"]
        
        # Pesos baseados na confiança
        conf0 = self.latest_predictions[active_sources[0]]["confidence"]
        conf1 = self.latest_predictions[active_sources[1]]["confidence"] if len(active_sources) > 1 else 0
        
        # Filtro de Dominância: Se uma câmera é muito superior (2.5x), usa apenas ela
        if len(active_sources) > 1:
            if conf0 > 2.5 * conf1:
                active_sources = [active_sources[0]]
            elif conf1 > 2.5 * conf0:
                active_sources = [active_sources[1]]

        # Se após o filtro restou apenas uma, repassa a predição dela
        if len(active_sources) == 1:
            single = self.latest_predictions[active_sources[0]].copy()
            single["source"] = "CAMERA"
            return single

        # Média Ponderada para as câmeras restantes
        total_conf = sum([self.latest_predictions[sid]["confidence"] for sid in active_sources])
        if total_conf == 0: total_conf = 1 # Evita divisão por zero
        
        for key in target_keys:
            weighted_sum = sum([self.latest_predictions[sid]["fingers"].get(key, 0) * self.latest_predictions[sid]["confidence"] for sid in active_sources])
            raw_angle = weighted_sum / total_conf
            
            # Aplica Filtro de Kalman sobre o resultado fundido
            fused_fingers[key] = int(self.kalman_filters[key].update(raw_angle))

        # Recalcular Gesture ID a partir dos dedos fundidos e filtrados
        new_gid = 0
        if fused_fingers.get("indicador", 0) > 125: new_gid += 1
        if fused_fingers.get("medio", 0) > 125: new_gid += 2
        if fused_fingers.get("anelar", 0) > 125: new_gid += 4
        if fused_fingers.get("minimo", 0) > 125: new_gid += 8
        if fused_fingers.get("polegar", 0) > 60: new_gid += 16

        display_id = new_gid % 16
        
        return {
            "prediction": self._get_gesture_name(display_id),
            "gesture_id": display_id,
            "confidence": int(total_conf / len(active_sources)),
            "fingers": fused_fingers,
            "source": "FUSION",
            "timestamp": now
        }

