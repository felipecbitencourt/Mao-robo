import cv2
import mediapipe as mp
import servo_braco3d as mao
import time

# --- Configuracao do MediaPipe Tasks API ---
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Inicializa o Reconhecedor de Gestos
options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='gesture_recognizer.task'),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5)

recognizer = GestureRecognizer.create_from_options(options)

# Inicializa Camera
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(3, 640)
cap.set(4, 480)

# Estado atual dos dedos (0 = Fechado, 1 = Aberto)
# Ordem: [Polegar, Indicador, Medio, Anelar, Minimo]
current_state = [1, 1, 1, 1, 1] 

def aplicar_configuracao_mao(nova_configuracao):
    """
    Recebe uma lista de 5 estados (0 ou 1) e aplica aos servos.
    Ex: [0, 0, 0, 0, 0] fecha a mao toda.
    """
    global current_state
    
    # Mapeamento: Indice Lista -> Pino Arduino
    # 0: Polegar -> Pin 10
    # 1: Indicador -> Pin 9
    # 2: Medio -> Pin 8
    # 3: Anelar -> Pin 7
    # 4: Minimo -> Pin 6
    pinos = [10, 9, 8, 7, 6]
    nomes = ["Polegar", "Indicador", "Medio", "Anelar", "Minimo"]

    for i in range(5):
        if nova_configuracao[i] != current_state[i]:
            current_state[i] = nova_configuracao[i]
            pino = pinos[i]
            estado = nova_configuracao[i]
            print(f"Servo {nomes[i]} (Pino {pino}) -> {estado}")
            mao.abrir_fechar(pino, estado)

print("Iniciando Controle por Gestos...")
print("Gestos Suportados: Closed_Fist, Open_Palm, Victory, Thumb_Up, Pointing_Up")

try:
    while True:
        success, img = cap.read()
        if not success:
            print("Frame vazio.")
            continue

        frameRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frameRGB)
        
        timestamp_ms = int(time.time() * 1000)
        
        # O resultado contem a lista de gestos detectados
        recognition_result = recognizer.recognize_for_video(mp_image, timestamp_ms)
        
        nome_gesto = "Nenhum"
        
        if recognition_result.gestures:
            # Pega o primeiro gesto da primeira mao
            top_gesture = recognition_result.gestures[0][0]
            nome_gesto = top_gesture.category_name
            score = top_gesture.score

            # Escreve na tela
            cv2.putText(img, f"Gesto: {nome_gesto} ({score:.2f})", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # --- Logica de Controle ---
            # [Polegar, Indicador, Medio, Anelar, Minimo]
            
            if nome_gesto == "Closed_Fist":
                aplicar_configuracao_mao([0, 0, 0, 0, 0])
                
            elif nome_gesto == "Open_Palm":
                aplicar_configuracao_mao([1, 1, 1, 1, 1])
                
            elif nome_gesto == "Victory":
                # V de Vitoria: Indicador e Medio abertos
                aplicar_configuracao_mao([0, 1, 1, 0, 0])
                
            elif nome_gesto == "Thumb_Up":
                # Joinha: So polegar aberto
                aplicar_configuracao_mao([1, 0, 0, 0, 0])
                
            elif nome_gesto == "Pointing_Up":
                # Apontando: So indicador aberto
                aplicar_configuracao_mao([0, 1, 0, 0, 0])
                
            elif nome_gesto == "ILoveYou":
                # Rock/Aranha: Polegar, Indicador e Mindinho
                # O modelo padrao as vezes detecta ILoveYou como Rock
                aplicar_configuracao_mao([1, 1, 0, 0, 1])

        else:
             cv2.putText(img, "Nenhum Gesto", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('Controle por Gestos', img)
        if cv2.waitKey(1) & 0xFF == 27:
            break

        if cv2.getWindowProperty('Controle por Gestos', cv2.WND_PROP_VISIBLE) < 1:
            break

except Exception as e:
    print(f"Ocorreu um erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    cap.release()
    cv2.destroyAllWindows()
    recognizer.close()
