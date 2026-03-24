"""
Modo Fluido - Controle proporcional dos dedos
Em vez de abrir/fechar (0/1), mapeia o angulo do dedo para posicao do servo.
"""
import cv2
import mediapipe as mp
import time
import numpy as np
import inspect

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
    base_options=BaseOptions(model_asset_path='hand_landmarker.task'),
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
cv2.namedWindow('Modo Fluido', cv2.WINDOW_NORMAL)

# Estado atual dos servos (para suavizacao)
posicao_atual = {pino: 0 for pino in PINOS.values()}

def calcular_angulo(a, b, c):
    """Calcula angulo entre 3 pontos (b e o vertice)"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

def mover_servo_suave(pino, posicao_alvo):
    """Move servo suavemente para posicao alvo"""
    global posicao_atual
    
    # Limitar posicao
    max_pos = VALORES_FECHADOS.get(pino, 140)
    posicao_alvo = max(0, min(max_pos, posicao_alvo))
    
    # Suavizacao (lerp)
    fator = 0.3  # Quanto maior, mais rapido
    nova_pos = posicao_atual[pino] + (posicao_alvo - posicao_atual[pino]) * fator
    nova_pos = int(nova_pos)
    
    # Só move se a diferença for significativa
    if abs(nova_pos - posicao_atual[pino]) >= 1:
        board.digital[pino].write(nova_pos)
        posicao_atual[pino] = nova_pos

def mapear_angulo_para_servo(angulo, pino):
    """
    Mapeia angulo do dedo (0-180 graus) para posicao do servo.
    Angulo ~180 = dedo reto = servo em 0 (aberto)
    Angulo ~60 = dedo fechado = servo no maximo
    """
    max_servo = VALORES_FECHADOS.get(pino, 140)
    
    # Inverter: angulo grande = aberto, angulo pequeno = fechado
    # Normalizar de 60-180 para 0-1
    angulo_normalizado = (angulo - 60) / 120  # 60-180 -> 0-1
    angulo_normalizado = max(0, min(1, angulo_normalizado))
    
    # Inverter e mapear para servo
    posicao = max_servo * (1 - angulo_normalizado)
    return posicao

print("Iniciando Modo Fluido...")
print("Movimente os dedos para ver o controle proporcional!")

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
            
            # Converter para coordenadas
            coords = [[lm.x * w, lm.y * h] for lm in landmarks]
            
            # Desenhar pontos
            for cx, cy in coords:
                cv2.circle(img, (int(cx), int(cy)), 4, (255, 0, 0), -1)
            
            # --- Calcular angulos dos dedos ---
            
            # Polegar: Distancia normalizada (nao usa angulo)
            p0, p5, p4, p17 = np.array(coords[0]), np.array(coords[5]), np.array(coords[4]), np.array(coords[17])
            palma = np.linalg.norm(p5 - p0)
            dist_polegar = np.linalg.norm(p17 - p4)
            ratio_polegar = dist_polegar / palma if palma > 0 else 1
            # Mapear ratio (0.5-1.3) para servo
            polegar_pos = VALORES_FECHADOS[10] * (1 - max(0, min(1, (ratio_polegar - 0.5) / 0.8)))
            mover_servo_suave(10, polegar_pos)
            
            # Indicador (angulo no PIP - junta 6)
            ang_indicador = calcular_angulo(coords[5], coords[6], coords[7])
            pos_indicador = mapear_angulo_para_servo(ang_indicador, 9)
            mover_servo_suave(9, pos_indicador)
            cv2.putText(img, f"Ind: {int(ang_indicador)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            
            # Medio (angulo no PIP - junta 10)
            ang_medio = calcular_angulo(coords[9], coords[10], coords[11])
            pos_medio = mapear_angulo_para_servo(ang_medio, 8)
            mover_servo_suave(8, pos_medio)
            cv2.putText(img, f"Med: {int(ang_medio)}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            
            # Anelar (angulo no PIP - junta 14)
            ang_anelar = calcular_angulo(coords[13], coords[14], coords[15])
            pos_anelar = mapear_angulo_para_servo(ang_anelar, 7)
            mover_servo_suave(7, pos_anelar)
            cv2.putText(img, f"Ane: {int(ang_anelar)}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            
            # Minimo (angulo no PIP - junta 18)
            ang_minimo = calcular_angulo(coords[17], coords[18], coords[19])
            pos_minimo = mapear_angulo_para_servo(ang_minimo, 6)
            mover_servo_suave(6, pos_minimo)
            cv2.putText(img, f"Min: {int(ang_minimo)}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            
            cv2.putText(img, "MODO FLUIDO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(img, "Mao nao detectada", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow('Modo Fluido', img)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break
        if cv2.getWindowProperty('Modo Fluido', cv2.WND_PROP_VISIBLE) < 1:
            break

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Abrir todos os dedos ao sair
    print("Abrindo todos os dedos...")
    for pino in PINOS.values():
        board.digital[pino].write(0)
        time.sleep(0.05)
    
    cap.release()
    cv2.destroyAllWindows()
    detector.close()
