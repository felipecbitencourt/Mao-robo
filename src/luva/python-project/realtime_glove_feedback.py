
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import queue
import os

PATH_TO_C_EXE = "./TestGlove64.exe" 
GLOVE_CONNECTION_PORT = "USB0" 
IMAGES_FOLDER = "../gesture-images" 

IMAGE_MAP = {
    0: "0.png",
    1: "1.png",
    2: "2.png",
    3: "3.png",
    4: "4.png",
    5: "5.png",
    6: "6.png",
    7: "7.png",
    8: "8.png",
    9: "9.png",
    10: "10.png",
    11: "11.png",
    12: "12.png",
    13: "13.png",
    14: "14.png",
    15: "15.png",
    -1: "-1.png",
}

# Nomes dos sensores 
SENSOR_NAMES = [
    "Thumb Near", "Thumb Far", "Thumb/Index", "Index Near", "Index Far",
    "Index/Middle", "Middle Near", "Middle Far", "Middle/Ring", "Ring Near",
    "Ring Far", "Ring/Little", "Little Near", "Little Far", 
    "Thumb Palm", "Wrist Bend", "Roll", "Pitch"
]


def read_from_c_bridge_thread(output_queue, c_exe_path, glove_port):
    try:
        print(f"Python: Iniciando a ponte C++ ({c_exe_path}) para comunicação com a luva...")
        process = subprocess.Popen(
            [c_exe_path, glove_port],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1
        )
        print("Python: Ponte C++ iniciada. Logs da ponte C++ aparecerão acima...")

        while True:
            output_line = process.stdout.readline()
            if not output_line:
                print("\nPython: A ponte C++ parou de enviar dados.")
                break
            
            try:
                output_queue.put(output_line.strip())
            except Exception as e:
                print(f"Python: Erro ao processar linha da ponte C++: {output_line.strip()} | Erro: {e}")
                
    except FileNotFoundError:
        print(f"Python: ERRO: O executável C++ '{c_exe_path}' não foi encontrado.")
        print("Python: Certifique-se de que compilaste o 'testglove.cpp' no Visual Studio e o caminho está correto.")
    except Exception as e:
        print(f"Python: Ocorreu um erro ao iniciar/ler da ponte C++: {e}")
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait()
            print("Python: Ponte C++ encerrada.")

class GloveFeedbackApp:
    def __init__(self, root, c_exe_path, glove_port):
        self.root = root
        self.root.title("Feedback da Luva 5DT - Neuroreabilitação")
        
        self.root.geometry("1000x800")
        self.root.resizable(False, False)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.images = self.load_images()
        
        self.max_amplitude = [1.1] * len(SENSOR_NAMES) 
        self.max_amplitude_reset_time = 0
        self.is_resetting = False
        self.max_opening_feedback_label = None

        self.c_exe_path = c_exe_path
        self.glove_port = glove_port

        self.setup_gui()
        self.queue = queue.Queue()
        self.c_thread = self.start_c_bridge_thread()
        self.root.after(100, self.process_queue)

    def load_images(self):
        images = {}
        for gesture_id, filename in IMAGE_MAP.items():
            path = os.path.join(IMAGES_FOLDER, filename)
            if os.path.exists(path):
                img = Image.open(path).resize((200, 200), Image.Resampling.LANCZOS)
                images[gesture_id] = ImageTk.PhotoImage(img)
            else:
                print(f"Aviso: Imagem '{path}' não encontrada.")
        return images

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill='both')

        feedback_frame = ttk.Frame(main_frame)
        feedback_frame.pack(side='left', padx=20, pady=20, fill='y')

        self.image_label = ttk.Label(feedback_frame)
        self.image_label.pack(pady=10)

        self.feedback_label_text = ttk.Label(
            feedback_frame,
            text="Iniciando...",
            font=("Helvetica", 36, "bold"),
            foreground="blue",
        )
        self.feedback_label_text.pack(pady=10)

        sensor_frame = ttk.Frame(main_frame)
        sensor_frame.pack(side='left', padx=20, pady=20, fill='y')
        
        ttk.Label(sensor_frame, text="Valores dos Sensores (0.0 a 1.0)", font=("Helvetica", 16, "bold")).pack(pady=5)
        
        self.sensor_labels = []
        for i, name in enumerate(SENSOR_NAMES):
            label = ttk.Label(sensor_frame, text=f"{name}: -", font=("Helvetica", 12))
            label.pack(anchor='w')
            self.sensor_labels.append(label)

        amplitude_frame = ttk.Frame(main_frame)
        amplitude_frame.pack(side='left', padx=20, pady=20, fill='both')
        
        ttk.Label(amplitude_frame, text="Amplitude Máxima de Abertura (Resetar a cada sessão)", font=("Helvetica", 16, "bold")).pack(pady=5)
        
        self.max_amplitude_labels = []
        for i, name in enumerate(SENSOR_NAMES):
            label = ttk.Label(amplitude_frame, text=f"{name}: -", font=("Helvetica", 12))
            label.pack(anchor='w')
            self.max_amplitude_labels.append(label)

        reset_button = ttk.Button(amplitude_frame, text="Iniciar Nova Sessão de Abertura", command=self.reset_max_amplitude)
        reset_button.pack(pady=20, anchor='center')

        self.max_opening_feedback_label = ttk.Label(amplitude_frame, text="", font=("Helvetica", 14), foreground="green")
        self.max_opening_feedback_label.pack(pady=5)

    def start_c_bridge_thread(self):
        thread = threading.Thread(
            target=read_from_c_bridge_thread, 
            args=(self.queue, self.c_exe_path, self.glove_port)
        )
        thread.daemon = True
        thread.start()
        return thread

    def reset_max_amplitude(self):
        self.max_amplitude = [1.1] * len(SENSOR_NAMES)
        self.is_resetting = True
        self.max_opening_feedback_label.config(text="Registrando nova amplitude... Mova a mão!", foreground="red")
        print("Amplitude máxima resetada. Mova a mão para registrar novos valores.")
        for i, label in enumerate(self.max_amplitude_labels):
            label.config(text=f"{SENSOR_NAMES[i]}: -")

    def process_queue(self):
        try:
            while True:
                data_string = self.queue.get_nowait()
                data_list = data_string.split(',')
                if len(data_list) != len(SENSOR_NAMES) + 1:
                    print(f"Aviso: Linha de dados com formato incorreto: {data_string}")
                    continue

                gesture_id = int(data_list[0])
                sensor_values = [float(v) for v in data_list[1:]]

                self.update_gui(gesture_id, sensor_values)
                self.update_max_amplitude(sensor_values)

        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_queue)

    def update_gui(self, gesture_id, sensor_values):
        image = self.images.get(gesture_id, self.images.get(-1))
        if image:
            self.image_label.config(image=image)
            self.image_label.image = image

        
        for i, value in enumerate(sensor_values):
            if i < len(self.sensor_labels):
                self.sensor_labels[i].config(text=f"{SENSOR_NAMES[i]}: {value:.3f}")

    def update_max_amplitude(self, current_sensor_values):
        for i, value in enumerate(current_sensor_values):
            if value < self.max_amplitude[i]:
                self.max_amplitude[i] = value
                
                self.max_amplitude_labels[i].config(text=f"{SENSOR_NAMES[i]}: {self.max_amplitude[i]:.3f}")

    def on_closing(self):
        print("\nPython: Fechando aplicação. Tentando encerrar a ponte C++...")
        self.root.destroy()


if __name__ == "__main__":
    if not os.path.exists(IMAGES_FOLDER):
        print(f"ERRO: A pasta de imagens '{IMAGES_FOLDER}' não foi encontrada.")
        print("Por favor, crie-a e adicione imagens para os gestos (flat_hand.png, fist.png, etc.).")
    else:
        root = tk.Tk()
        app = GloveFeedbackApp(root, PATH_TO_C_EXE, GLOVE_CONNECTION_PORT)
        root.mainloop()