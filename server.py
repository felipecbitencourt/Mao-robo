import cv2
import mediapipe as mp
import time
import numpy as np
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import threading
from typing import List
from collections import deque

# Importando lógica existente
import servo_braco3d as hardware
from eeg_brainlink import BrainLinkEEG, BrainLinkData

app = FastAPI()

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HardwareService:
    def __init__(self):
        self.running = False
        self.mode = "gestures" # "gestures" ou "eeg"
        self.telemetry = {
            "hand_detected": False,
            "fingers": {"polegar": 0, "indicador": 0, "medio": 0, "anelar": 0, "minimo": 0},
            "eeg": {"attention": 0, "meditation": 0, "signal": 200, "battery": 0}
        }
        self.eeg = None
        self.cap = None
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def _loop(self):
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.cap = cv2.VideoCapture(0)
        
        # Histórico para suavização (simplificado)
        buffer_angulos = {dedo: deque(maxlen=5) for dedo in ["polegar", "indicador", "medio", "anelar", "minimo"]}
        
        while self.running:
            if self.mode == "gestures":
                success, frame = self.cap.read()
                if not success: continue
                
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb_frame)
                
                if results.multi_hand_landmarks:
                    self.telemetry["hand_detected"] = True
                    # Extraindo coordenadas para cálculo
                    landmarks = results.multi_hand_landmarks[0]
                    h, w, _ = frame.shape
                    coords = [[lm.x * w, lm.y * h] for lm in landmarks.landmark]
                    
                    # Logica de main_fluido_v2.py aqui...
                    # (Calculando ângulos e movendo servos via hardware.abrir_fechar ou board.digital[pino].write)
                    # Para simplificar este passo, vamos apenas atualizar a telemetria com se está "fechado" ou "aberto"
                    self.telemetry["fingers"] = self._calculate_finger_states(coords)
                else:
                    self.telemetry["hand_detected"] = False
                    
            elif self.mode == "eeg":
                # ... lógica EEG ...
                pass
            
            time.sleep(0.01)

    def _calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        if angle > 180.0: angle = 360 - angle
        return angle

    def _calculate_finger_states(self, coords):
        indices = {
            'indicador': {'mcp': (0, 5, 6), 'pip': (5, 6, 7)},
            'medio':     {'mcp': (0, 9, 10), 'pip': (9, 10, 11)},
            'anelar':    {'mcp': (0, 13, 14), 'pip': (13, 14, 15)},
            'minimo':    {'mcp': (0, 17, 18), 'pip': (17, 18, 19)}
        }
        states = {}
        for finger, joints in indices.items():
            ang_mcp = self._calculate_angle(coords[joints['mcp'][0]], coords[joints['mcp'][1]], coords[joints['mcp'][2]])
            ang_pip = self._calculate_angle(coords[joints['pip'][0]], coords[joints['pip'][1]], coords[joints['pip'][2]])
            # Média ponderada como no main_fluido_v2
            avg_angle = ang_mcp * 0.3 + ang_pip * 0.7
            states[finger] = int(avg_angle)
            
        # Polegar (distância simplificada)
        p5, p4, p17 = np.array(coords[5]), np.array(coords[4]), np.array(coords[17])
        dist = np.linalg.norm(p17 - p4) / np.linalg.norm(p5 - np.array(coords[0]))
        states["polegar"] = int(dist * 100)
        
        return states

    def _loop(self):
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.cap = cv2.VideoCapture(0)
        
        # EEG setup
        from eeg_brainlink import BrainLinkEEG
        self.eeg = BrainLinkEEG(port='COM6') # Ajuste conforme necessário
        eeg_connected = self.eeg.connect()

        while self.running:
            if self.mode == "gestures":
                success, frame = self.cap.read()
                if success:
                    frame = cv2.flip(frame, 1)
                    results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.multi_hand_landmarks:
                        self.telemetry["hand_detected"] = True
                        h, w, _ = frame.shape
                        coords = [[lm.x * w, lm.y * h] for lm in results.multi_hand_landmarks[0].landmark]
                        self.telemetry["fingers"] = self._calculate_finger_states(coords)
                        
                        # Mover servos
                        for finger, value in self.telemetry["fingers"].items():
                            # Mapeamento simplificado para exemplo
                            # hardware.board.digital[PINO].write(value) 
                            pass
                    else:
                        self.telemetry["hand_detected"] = False
            
            elif self.mode == "eeg" and eeg_connected:
                self.eeg.read_once()
                self.telemetry["eeg"] = {
                    "attention": self.eeg.get_attention(),
                    "meditation": self.eeg.get_meditation(),
                    "signal": self.eeg.parser.data.signal if self.eeg.parser else 200,
                    "battery": self.eeg.parser.data.battery if self.eeg.parser else 0
                }
            
            time.sleep(0.05)

service = HardwareService()

@app.on_event("startup")
async def startup_event():
    service.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Envia telemetria a cada 100ms
            await websocket.send_json(service.telemetry)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")

@app.post("/set_mode")
async def set_mode(mode: str):
    if mode in ["gestures", "eeg"]:
        service.mode = mode
        return {"status": "ok", "mode": mode}
    return {"status": "error", "message": "Invalid mode"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
