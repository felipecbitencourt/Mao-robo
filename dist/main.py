import cv2
import mediapipe as mp
import servo_braco3d as mao
import time
import numpy as np

# --- Configuracao ---
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Inicializa o Reconhecedor
options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='gesture_recognizer.task'),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5)

recognizer = GestureRecognizer.create_from_options(options)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(3, 1280)
cap.set(4, 720)

cv2.namedWindow('Hibrido', cv2.WINDOW_NORMAL)

# Estado atual [Polegar, Indicador, Medio, Anelar, Minimo]
current_state = [1, 1, 1, 1, 1] 

def aplicar_configuracao(nova_config, nome_gesto):
    global current_state
    pinos = [10, 9, 8, 7, 6]
    
    mudou = False
    for i in range(5):
        if nova_config[i] != current_state[i]:
            current_state[i] = nova_config[i]
            mao.abrir_fechar(pinos[i], nova_config[i])
            mudou = True
            
    if mudou:
        print(f"Gesto Detectado: {nome_gesto} -> {nova_config}")

def calcular_angulo(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0: angle = 360 - angle
    return angle

def analisar_gestos_customizados(landmarks, img_w, img_h):
    """
    Se a IA nao reconhecer nada, usamos matematica para achar outros gestos.
    Retorna (NomeDoGesto, ListaDeEstados) ou None.
    """
    coords = []
    for lm in landmarks:
        coords.append([lm.x * img_w, lm.y * img_h])
        
    # Verifica quais dedos estao "Retos" (Abertos) usando angulos
    # Indices PIP: Indicador(6), Medio(10), Anelar(14), Minimo(18)
    dedos_abertos = [False] * 5
    
    # 1. Polegar (Baseado em distancia relativa, simplificado)
    # Comparando distancia PontaPolegar(4)-Minimo(17) vs Palma
    p0, p5, p4, p17 = np.array(coords[0]), np.array(coords[5]), np.array(coords[4]), np.array(coords[17])
    if np.linalg.norm(p17 - p4) / np.linalg.norm(p5 - p0) > 0.9:
        dedos_abertos[0] = True # Aberto

    # 2. Outros dedos (Simplesmente angulo > 150)
    indices_triplet = [(5,6,7), (9,10,11), (13,14,15), (17,18,19)]
    for i, triplet in enumerate(indices_triplet):
        ang = calcular_angulo(coords[triplet[0]], coords[triplet[1]], coords[triplet[2]])
        if ang > 150:
            dedos_abertos[i+1] = True # i+1 pq o 0 e o polegar

    # --- Regras Customizadas ---
    # Python converte boolean para 0 ou 1 automaticamente
    estados = [1 if d else 0 for d in dedos_abertos]
    
    # [Polegar, Indicador, Medio, Anelar, Minimo]
    
    # Rock / Metal (Indicador + Minimo)
    if dedos_abertos[1] and dedos_abertos[4] and not dedos_abertos[2] and not dedos_abertos[3]:
        return "Rock / Metal", [0, 1, 0, 0, 1] # Polegar fechado para ficar mais claro
        
    # Hang Loose (Polegar + Minimo)
    if dedos_abertos[0] and dedos_abertos[4] and not dedos_abertos[1] and not dedos_abertos[2]:
        return "Hang Loose", estados
        
    # Faz o L (Polegar + Indicador)
    if dedos_abertos[0] and dedos_abertos[1] and not dedos_abertos[2] and not dedos_abertos[3] and not dedos_abertos[4]:
        return "Faz o L", estados
    
    # Contagem: 3 Dedos (Indicador, Medio, Anelar)
    if dedos_abertos[1] and dedos_abertos[2] and dedos_abertos[3] and not dedos_abertos[4]:
        return "Numero 3", estados
        
    # Contagem: 4 Dedos (Todos menos polegar)
    if not dedos_abertos[0] and all(dedos_abertos[1:]):
        return "Numero 4", estados

    # Se nao for nenhum especial, retorna o estado fisico detectado (Modo Livre)
    return "Modo Livre", estados

print("Iniciando Sistema Hibrido (IA + Regras)...")

try:
    while True:
        success, img = cap.read()
        if not success: continue

        img = cv2.flip(img, 1) # Espelhar a imagem

        frameRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frameRGB)
        timestamp_ms = int(time.time() * 1000)
        
        result = recognizer.recognize_for_video(mp_image, timestamp_ms)
        h, w, _ = img.shape

        nome_final = "Nenhum"
        cor_texto = (0, 0, 255)

        if result.gestures:
            top_gesture = result.gestures[0][0]
            nome_ia = top_gesture.category_name
            score = top_gesture.score
            
            # Se a IA tem certeza (> 0.6), usamos ela para os classicos
            if nome_ia != "None" and score > 0.6:
                nome_final = f"IA: {nome_ia}"
                cor_texto = (0, 255, 0)
                
                if nome_ia == "Closed_Fist": aplicar_configuracao([0,0,0,0,0], nome_ia)
                elif nome_ia == "Open_Palm": aplicar_configuracao([1,1,1,1,1], nome_ia)
                elif nome_ia == "Victory": aplicar_configuracao([0,1,1,0,0], nome_ia)
                elif nome_ia == "Thumb_Up": aplicar_configuracao([1,0,0,0,0], nome_ia)
                elif nome_ia == "Pointing_Up": aplicar_configuracao([0,1,0,0,0], nome_ia)
                elif nome_ia == "ILoveYou": aplicar_configuracao([1,1,0,0,1], nome_ia)
            
            # Se a IA nao sabe ("None") ou esta confusa, usamos nossa logica
            elif result.hand_landmarks:
                nome_custom, estados = analisar_gestos_customizados(result.hand_landmarks[0], w, h)
                nome_final = f"Custom: {nome_custom}"
                cor_texto = (255, 255, 0)
                aplicar_configuracao(estados, nome_custom)
                
                # Desenho simples
                for lm in result.hand_landmarks[0]:
                    cv2.circle(img, (int(lm.x*w), int(lm.y*h)), 3, (255,0,0), -1)

        cv2.putText(img, nome_final, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, cor_texto, 2)
        cv2.imshow('Hibrido', img)
        if cv2.waitKey(1) & 0xFF == 27:
            break
        
        # Se a janela foi fechada pelo 'X'
        if cv2.getWindowProperty('Hibrido', cv2.WND_PROP_VISIBLE) < 1:
            break

except Exception as e:
    print(e)
finally:
    # Abrir todos os dedos ao fechar o programa
    print("Abrindo todos os dedos...")
    for pino in [10, 9, 8, 7, 6]:
        mao.abrir_fechar(pino, 1)  # 1 = Abrir
    
    cap.release()
    cv2.destroyAllWindows()
    recognizer.close()

