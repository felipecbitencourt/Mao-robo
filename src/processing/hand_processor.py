import mediapipe as mp
import cv2
import numpy as np
import time
import queue
import os
from PySide6.QtCore import QObject, QThread, Signal

from core.paths import resource_path

class HandProcessor(QThread):
    prediction_signal = Signal(dict)
    processed_frame_signal = Signal(object) # Envia frame com os pontos desenhados

    def __init__(self, model_path="models/hand_landmarker.task"):
        super().__init__()
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.model_path = resource_path(model_path)
        
        # Configuração MediaPipe Tasks (Idêntico ao main_fluido_v2.py)
        self.BaseOptions = mp.tasks.BaseOptions
        self.HandLandmarker = mp.tasks.vision.HandLandmarker
        self.HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        self.VisionRunningMode = mp.tasks.vision.RunningMode
        
        self.detector = None
        
        # Índices para cada dedo conforme main_fluido_v2
        self.INDICES_DEDOS = {
            'indicador': {'mcp': (0, 5, 6), 'pip': (5, 6, 7), 'bit': 0},
            'medio':     {'mcp': (0, 9, 10), 'pip': (9, 10, 11), 'bit': 1},
            'anelar':    {'mcp': (0, 13, 14), 'pip': (13, 14, 15), 'bit': 2},
            'minimo':    {'mcp': (0, 17, 18), 'pip': (17, 18, 19), 'bit': 3}
        }

    def process_frame(self, frame):
        """Enfileira frame para processamento"""
        if not self.frame_queue.full():
            self.frame_queue.put(frame)

    def run(self):
        # Carrega o modelo como buffer para evitar problemas com caracteres especiais no caminho (ex: "Códigos")
        with open(self.model_path, 'rb') as f:
            model_buffer = f.read()

        # Inicializa o detector
        options = self.HandLandmarkerOptions(
            base_options=self.BaseOptions(model_asset_buffer=model_buffer),
            running_mode=self.VisionRunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = self.HandLandmarker.create_from_options(options)

        self.running = True
        
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                self._analyze_frame(frame)
            except queue.Empty:
                continue
        
        if self.detector:
            self.detector.close()

    def stop(self):
        self.running = False
        self.wait()

    def _analyze_frame(self, frame):
        """Analisa frame e desenha pontos como no main_fluido_v2.py"""
        if frame is None or self.detector is None: return
        
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(time.time() * 1000)
        
        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        
        gesture_id = 0
        confidence = 0
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
        
        # Emitir o frame processado com os pontos desenhados
        self.processed_frame_signal.emit(processed_frame)

        self.prediction_signal.emit({
            "prediction": self._get_gesture_name(display_id),
            "gesture_id": display_id,
            "confidence": confidence,
            "fingers": fingers_state,
            "timestamp": time.time()
        })

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
