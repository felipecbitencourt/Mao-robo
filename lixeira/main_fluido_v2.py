"""
Modo Fluido V2 - Com multiplos angulos e suavizacao temporal
Usa 2 angulos por dedo (MCP e PIP) + media dos ultimos N frames
"""
import cv2
import mediapipe as mp
import time
import numpy as np
import os
import sys

# Adiciona a pasta src ao path para encontrar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import inspect
from collections import deque

# Fix para pyfirmata em Python 3.13
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

from pyfirmata import Arduino, SERVO

# --- Configuracao Arduino ---
PORTA_COM = 'COM5'
board = Arduino(PORTA_COM)

# Pinos dos servos
PINOS = {
    'polegar': 10,
    'indicador': 9,
    'medio': 8,
    'anelar': 7,
    'minimo': 6
}

# Valores calibrados (0 = aberto, valor = fechado)
VALORES_FECHADOS = {
    10: 150,  # Polegar
    9: 180,   # Indicador
    8: 160,   # Medio
    7: 180,   # Anelar
    6: 130    # Minimo
}

# Configurar pinos como SERVO
for pino in PINOS.values():
    board.digital[pino].mode = SERVO

# --- Configuracao MediaPipe ---
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='models/hand_landmarker.task'),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5)

detector = HandLandmarker.create_from_options(options)

# --- Camera ---
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(3, 1280)
cap.set(4, 720)
cv2.namedWindow('Modo Fluido V2', cv2.WINDOW_NORMAL)

# Estado atual dos servos
posicao_atual = {pino: 0 for pino in PINOS.values()}

# Buffer para media temporal (ultimos N angulos)
BUFFER_SIZE = 5
historico_angulos = {
    'polegar': deque(maxlen=BUFFER_SIZE),
    'indicador': deque(maxlen=BUFFER_SIZE),
    'medio': deque(maxlen=BUFFER_SIZE),
    'anelar': deque(maxlen=BUFFER_SIZE),
    'minimo': deque(maxlen=BUFFER_SIZE)
}

def calcular_angulo(a, b, c):
    """Calcula angulo entre 3 pontos (b e o vertice)"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

def media_temporal(nome_dedo, novo_valor):
    """Adiciona valor ao buffer e retorna media"""
    historico_angulos[nome_dedo].append(novo_valor)
    return np.mean(historico_angulos[nome_dedo])

def mover_servo_suave(pino, posicao_alvo):
    """Move servo suavemente para posicao alvo"""
    global posicao_atual
    
    max_pos = VALORES_FECHADOS.get(pino, 140)
    posicao_alvo = max(0, min(max_pos, posicao_alvo))
    
    # Suavizacao mais responsiva
    fator = 0.4
    nova_pos = posicao_atual[pino] + (posicao_alvo - posicao_atual[pino]) * fator
    nova_pos = int(nova_pos)
    
    if abs(nova_pos - posicao_atual[pino]) >= 1:
        board.digital[pino].write(nova_pos)
        posicao_atual[pino] = nova_pos

def calcular_angulo_dedo(coords, indices_mcp, indices_pip):
    """
    Calcula media de 2 angulos por dedo:
    - Angulo no MCP (base do dedo)
    - Angulo no PIP (meio do dedo)
    """
    ang_mcp = calcular_angulo(coords[indices_mcp[0]], coords[indices_mcp[1]], coords[indices_mcp[2]])
    ang_pip = calcular_angulo(coords[indices_pip[0]], coords[indices_pip[1]], coords[indices_pip[2]])
    
    # Peso maior para PIP (mais indicativo de flexao)
    return ang_mcp * 0.3 + ang_pip * 0.7

def mapear_angulo_para_servo(angulo, pino):
    max_servo = VALORES_FECHADOS.get(pino, 140)
    
    # Angulo 180 = reto (aberto), 60 = fechado
    angulo_normalizado = (angulo - 60) / 120
    angulo_normalizado = max(0, min(1, angulo_normalizado))
    
    posicao = max_servo * (1 - angulo_normalizado)
    return posicao

# Indices para cada dedo: [ponto_antes, junta, ponto_depois]
INDICES_DEDOS = {
    'indicador': {'mcp': (0, 5, 6), 'pip': (5, 6, 7)},
    'medio':     {'mcp': (0, 9, 10), 'pip': (9, 10, 11)},
    'anelar':    {'mcp': (0, 13, 14), 'pip': (13, 14, 15)},
    'minimo':    {'mcp': (0, 17, 18), 'pip': (17, 18, 19)}
}

print("Iniciando Modo Fluido V2...")
print("Usando 2 angulos por dedo + media temporal de 5 frames")

try:
    while True:
        success, img = cap.read()
        if not success:
            continue

        img = cv2.flip(img, 1)
        frameRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frameRGB)
        timestamp_ms = int(time.time() * 1000)

        result = detector.detect_for_video(mp_image, timestamp_ms)
        h, w, _ = img.shape

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            coords = [[lm.x * w, lm.y * h] for lm in landmarks]
            
            # Desenhar pontos
            for i, (cx, cy) in enumerate(coords):
                cor = (0, 255, 0) if i in [5, 6, 9, 10, 13, 14, 17, 18] else (255, 0, 0)
                cv2.circle(img, (int(cx), int(cy)), 5, cor, -1)
            
            # --- Polegar (usa distancia) ---
            p0, p5, p4, p17 = np.array(coords[0]), np.array(coords[5]), np.array(coords[4]), np.array(coords[17])
            palma = np.linalg.norm(p5 - p0)
            dist_polegar = np.linalg.norm(p17 - p4)
            ratio = dist_polegar / palma if palma > 0 else 1
            ratio_suave = media_temporal('polegar', ratio)
            polegar_pos = VALORES_FECHADOS[10] * (1 - max(0, min(1, (ratio_suave - 0.5) / 0.8)))
            mover_servo_suave(10, polegar_pos)
            
            y_pos = 30
            
            # --- Outros dedos (2 angulos cada) ---
            for nome, indices in INDICES_DEDOS.items():
                pino = PINOS[nome]
                
                # Calcular media de 2 angulos
                ang_combinado = calcular_angulo_dedo(coords, indices['mcp'], indices['pip'])
                
                # Aplicar media temporal
                ang_suave = media_temporal(nome, ang_combinado)
                
                # Mapear para servo
                pos = mapear_angulo_para_servo(ang_suave, pino)
                mover_servo_suave(pino, pos)
                
                # Mostrar na tela
                cv2.putText(img, f"{nome[:3].upper()}: {int(ang_suave)}", (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                y_pos += 30
            
            cv2.putText(img, "MODO FLUIDO V2 (2 angulos + temporal)", (10, h-20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(img, "Mao nao detectada", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow('Modo Fluido V2', img)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break
        if cv2.getWindowProperty('Modo Fluido V2', cv2.WND_PROP_VISIBLE) < 1:
            break

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("Abrindo todos os dedos...")
    for pino in PINOS.values():
        board.digital[pino].write(0)
        time.sleep(0.05)
    
    cap.release()
    cv2.destroyAllWindows()
    detector.close()
