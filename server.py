import os
import sys
import cv2
import mediapipe as mp
import time
import numpy as np
import asyncio
import threading
from contextlib import asynccontextmanager
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Adiciona a pasta src ao path para encontrar os módulos (core, hardware, etc),
# do mesmo modo que o main.py faz.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from core.config_manager import ConfigManager
from hardware.eeg_brainlink import BrainLinkEEG


class HardwareService:
    def __init__(self):
        self.running = False
        self.mode = "gestures"  # "gestures" ou "eeg"
        self.telemetry = {
            "hand_detected": False,
            "fingers": {"polegar": 0, "indicador": 0, "medio": 0, "anelar": 0, "minimo": 0},
            "eeg": {"attention": 0, "meditation": 0, "signal": 200, "battery": 0}
        }
        self.eeg = None
        self.cap = None
        self.thread = None

        # Portas e câmera vêm do config.json, o mesmo usado pela interface desktop
        self.config = ConfigManager()
        self.eeg_port = self.config.get("eeg_port", "COM10")
        self.camera_index = self.config.get("camera_index", 0)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.eeg:
            self.eeg.disconnect()
            self.eeg = None

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
        self.cap = cv2.VideoCapture(self.camera_index)

        # EEG é opcional: se a tiara não estiver conectada o modo "gestures" segue funcionando
        eeg_connected = False
        try:
            self.eeg = BrainLinkEEG(port=self.eeg_port)
            eeg_connected = self.eeg.connect()
        except Exception as e:
            print(f"[server] EEG indisponivel em {self.eeg_port}: {e}")

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
                        # NOTA: este protótipo apenas publica telemetria; o acionamento dos
                        # servos nunca foi implementado aqui. Para mover a mão de verdade,
                        # use a interface desktop (main.py), que passa por
                        # src/outputs/arduino_output.py.
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.start()
    yield
    service.stop()


app = FastAPI(lifespan=lifespan)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
