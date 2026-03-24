import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import queue
import os

# ============================================================
# CONFIGURAÇÕES
# ============================================================
PATH_TO_C_EXE = "./TestGlove64.exe"
GLOVE_CONNECTION_PORT = "USB0"
IMAGES_FOLDER = "../gesture-images"

IMAGE_MAP = {
    0: "0.png", 1: "1.png", 2: "2.png", 3: "3.png", 4: "4.png",
    5: "5.png", 6: "6.png", 7: "7.png", 8: "8.png", 9: "9.png",
    10: "10.png", 11: "11.png", 12: "12.png", 13: "13.png",
    14: "14.png", 15: "15.png", -1: "-1.png",
}

SENSOR_NAMES = [
    "Thumb Near", "Thumb Far", "Thumb/Index", "Index Near", "Index Far",
    "Index/Middle", "Middle Near", "Middle Far", "Middle/Ring", "Ring Near",
    "Ring Far", "Ring/Little", "Little Near", "Little Far",
    "Thumb Palm", "Wrist Bend", "Roll", "Pitch"
]

# ============================================================
# THREAD DE COMUNICAÇÃO
# ============================================================
def read_from_glove_thread(output_queue, status_queue, c_exe_path, glove_port):
    try:
        process = subprocess.Popen(
            [c_exe_path, glove_port],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        status_queue.put("connected")
        
        while True:
            output_line = process.stdout.readline()
            if not output_line:
                status_queue.put("disconnected")
                break
            output_queue.put(output_line.strip())
                
    except FileNotFoundError:
        status_queue.put("error_not_found")
    except Exception as e:
        status_queue.put(f"error_{str(e)}")
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait()

# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================
class ClinicalGloveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Neuroreabilitação - Luva 5DT")
        self.root.geometry("1200x800")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f4f8')
        
        self.glove_connected = False
        self.calibration_active = False
        self.feedback_active = False
        self.calibration_count = 0
        
        # Calibração: armazena valores máximos e mínimos de cada ciclo
        self.calibration_max_per_cycle = []  # Lista de listas: [[max_sensor0, max_sensor1, ...], ...]
        self.calibration_min_per_cycle = []  # Lista de listas: [[min_sensor0, min_sensor1, ...], ...]
        self.current_cycle_max = None
        self.current_cycle_min = None
        
        # Valores finais de calibração
        self.sensor_max_values = [0.0] * len(SENSOR_NAMES)  # Média dos máximos
        self.sensor_min_values = [1.0] * len(SENSOR_NAMES)  # Média dos mínimos
        self.sensor_threshold = [0.5] * len(SENSOR_NAMES)   # Ponto médio entre max e min
        
        # Estado dos dedos (True = fechado, False = aberto)
        self.finger_states = [False] * len(SENSOR_NAMES)
        
        self.images = self.load_images()
        self.data_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.c_thread = None
        
        self.setup_main_screen()
        self.root.after(100, self.check_status)
        self.root.after(100, self.process_data)
        self.start_connection()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_images(self):
        """Carrega todas as imagens de gestos"""
        images = {}
        for gesture_id, filename in IMAGE_MAP.items():
            path = os.path.join(IMAGES_FOLDER, filename)
            if os.path.exists(path):
                img = Image.open(path).resize((400, 400), Image.Resampling.LANCZOS)
                images[gesture_id] = ImageTk.PhotoImage(img)
            else:
                print(f"Aviso: Imagem '{path}' não encontrada.")
        return images

    def setup_main_screen(self):
        self.clear_screen()
        main_container = tk.Frame(self.root, bg='#f0f4f8')
        main_container.pack(expand=True, fill='both', padx=40, pady=40)
        
        title = tk.Label(main_container, text="Sistema de Neuroreabilitação",
                        font=("Helvetica", 28, "bold"), bg='#f0f4f8', fg='#1a202c')
        title.pack(pady=(0, 10))
        
        subtitle = tk.Label(main_container, text="Luva 5DT - Reconhecimento de Gestos em Tempo Real",
                           font=("Helvetica", 16), bg='#f0f4f8', fg='#4a5568')
        subtitle.pack(pady=(0, 40))
        
        status_card = tk.Frame(main_container, bg='white', relief='raised', borderwidth=2)
        status_card.pack(pady=20, ipadx=40, ipady=30)
        
        status_label = tk.Label(status_card, text="Status da Luva",
                               font=("Helvetica", 18, "bold"), bg='white', fg='#2d3748')
        status_label.pack(pady=(0, 20))
        
        led_frame = tk.Frame(status_card, bg='white')
        led_frame.pack(pady=10)
        
        self.led_canvas = tk.Canvas(led_frame, width=60, height=60, bg='white', highlightthickness=0)
        self.led_canvas.pack(side='left', padx=10)
        self.led_indicator = self.led_canvas.create_oval(10, 10, 50, 50, fill='#ef4444', 
                                                         outline='#dc2626', width=3)
        
        self.status_text = tk.Label(led_frame, text="Desconectado",
                                   font=("Helvetica", 20, "bold"), bg='white', fg='#ef4444')
        self.status_text.pack(side='left', padx=10)
        
        self.start_calibration_btn = tk.Button(
            main_container, text="Iniciar Calibração", font=("Helvetica", 16, "bold"),
            bg='#3b82f6', fg='white', activebackground='#2563eb', activeforeground='white',
            padx=40, pady=15, cursor='hand2', state='disabled',
            command=self.show_calibration_instructions
        )
        self.start_calibration_btn.pack(pady=30)
        
        info_frame = tk.Frame(main_container, bg='#e2e8f0', relief='flat', borderwidth=1)
        info_frame.pack(pady=20, fill='x', padx=50)
        
        info_text = """📋 Instruções:

1. Conecte a luva 5DT ao computador
2. Aguarde o indicador verde de conexão
3. Clique em "Iniciar Calibração" para começar
4. Visualize os gestos reconhecidos em tempo real!"""
        
        info_label = tk.Label(info_frame, text=info_text, font=("Helvetica", 12),
                             bg='#e2e8f0', fg='#2d3748', justify='left')
        info_label.pack(padx=20, pady=15)

    def show_calibration_instructions(self):
        self.clear_screen()
        container = tk.Frame(self.root, bg='#f0f4f8')
        container.pack(expand=True, fill='both', padx=50, pady=50)
        
        title = tk.Label(container, text="Protocolo de Calibração",
                        font=("Helvetica", 26, "bold"), bg='#f0f4f8', fg='#1a202c')
        title.pack(pady=(0, 30))
        
        instructions_card = tk.Frame(container, bg='white', relief='raised', borderwidth=2)
        instructions_card.pack(fill='both', expand=True, padx=40, pady=20)
        
        instructions_text = """📝 Instruções do Protocolo de Calibração

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Durante a calibração você realizará:

• 10 ciclos de abertura e fechamento da mão
• Cada movimento terá duração de 5 segundos
• O sistema registrará os valores máximos e mínimos de cada sensor
• Após os 10 ciclos, será calculado o ponto médio de cada sensor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  IMPORTANTE:

✓ Mantenha a mão relaxada antes de iniciar
✓ Execute os movimentos de forma natural e completa
✓ ABRA a mão ao MÁXIMO quando solicitado
✓ FECHE a mão ao MÁXIMO quando solicitado
✓ Mantenha o punho estável durante os movimentos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Objetivo: O sistema aprenderá seus limites individuais de movimento
para melhor detecção de gestos!

A calibração levará aproximadamente 2 minutos."""
        
        instructions_label = tk.Label(instructions_card, text=instructions_text,
                                     font=("Courier", 10), bg='white', fg='#2d3748', justify='left')
        instructions_label.pack(padx=30, pady=30)
        
        button_frame = tk.Frame(container, bg='#f0f4f8')
        button_frame.pack(pady=20)
        
        back_btn = tk.Button(button_frame, text="← Voltar", font=("Helvetica", 14),
                            bg='#6b7280', fg='white', activebackground='#4b5563',
                            padx=30, pady=12, cursor='hand2', command=self.setup_main_screen)
        back_btn.pack(side='left', padx=10)
        
        start_btn = tk.Button(button_frame, text="Iniciar Protocolo →",
                             font=("Helvetica", 14, "bold"), bg='#10b981', fg='white',
                             activebackground='#059669', padx=30, pady=12, cursor='hand2',
                             command=self.start_calibration)
        start_btn.pack(side='left', padx=10)

    def start_calibration(self):
        self.clear_screen()
        self.calibration_active = True
        self.calibration_count = 0
        self.calibration_max_per_cycle = []
        self.calibration_min_per_cycle = []
        
        container = tk.Frame(self.root, bg='#f0f4f8')
        container.pack(expand=True, fill='both')
        
        self.calibration_counter = tk.Label(container, text="Calibração 1/10",
                                           font=("Helvetica", 20, "bold"),
                                           bg='#f0f4f8', fg='#3b82f6')
        self.calibration_counter.pack(pady=20)
        
        self.calibration_instruction = tk.Label(container, text="",
                                               font=("Helvetica", 32, "bold"),
                                               bg='#f0f4f8', fg='#1a202c', wraplength=800)
        self.calibration_instruction.pack(pady=40)
        
        self.timer_canvas = tk.Canvas(container, width=400, height=400,
                                      bg='#f0f4f8', highlightthickness=0)
        self.timer_canvas.pack(pady=20)
        
        progress_frame = tk.Frame(container, bg='#f0f4f8')
        progress_frame.pack(pady=30, fill='x', padx=100)
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=800,
                                           mode='determinate', maximum=10)
        self.progress_bar.pack()
        
        self.root.after(1000, self.calibration_cycle)

    def calibration_cycle(self):
        if self.calibration_count >= 10:
            self.finish_calibration()
            return
        
        self.calibration_count += 1
        self.calibration_counter.config(text=f"Calibração {self.calibration_count}/10")
        self.progress_bar['value'] = self.calibration_count
        
        # Inicializar rastreamento do ciclo atual
        self.current_cycle_max = [0.0] * len(SENSOR_NAMES)
        self.current_cycle_min = [1.0] * len(SENSOR_NAMES)
        
        self.calibration_instruction.config(text="✋ ABRA A MÃO COMPLETAMENTE", fg='#10b981')
        self.animate_timer(5, '#10b981', lambda: self.close_hand_phase())
    
    def close_hand_phase(self):
        self.calibration_instruction.config(text="✊ FECHE A MÃO COMPLETAMENTE", fg='#ef4444')
        self.animate_timer(5, '#ef4444', lambda: self.end_cycle())
    
    def end_cycle(self):
        """Finaliza o ciclo atual e salva os valores máximos e mínimos"""
        self.calibration_max_per_cycle.append(self.current_cycle_max[:])
        self.calibration_min_per_cycle.append(self.current_cycle_min[:])
        
        print(f"Ciclo {self.calibration_count} completo:")
        print(f"  Máximos: {[f'{v:.3f}' for v in self.current_cycle_max]}")
        print(f"  Mínimos: {[f'{v:.3f}' for v in self.current_cycle_min]}")
        
        self.calibration_cycle()
    
    def animate_timer(self, seconds, color, callback):
        self.timer_canvas.delete('all')
        
        def draw_arc(remaining):
            if remaining < 0 or not self.calibration_active:
                callback()
                return
            
            self.timer_canvas.delete('all')
            self.timer_canvas.create_oval(50, 50, 350, 350, outline='#e5e7eb', width=15)
            
            extent = -(360 * remaining / seconds)
            self.timer_canvas.create_arc(50, 50, 350, 350, start=90, extent=extent,
                                        outline=color, width=15, style='arc')
            
            self.timer_canvas.create_text(200, 200, text=str(int(remaining) + 1),
                                         font=("Helvetica", 80, "bold"), fill=color)
            
            self.root.after(100, lambda: draw_arc(remaining - 0.1))
        
        draw_arc(seconds)

    def finish_calibration(self):
        """Calcula as médias dos valores máximos e mínimos e define os thresholds"""
        self.calibration_active = False
        
        # Calcular média dos máximos e mínimos
        num_cycles = len(self.calibration_max_per_cycle)
        
        for i in range(len(SENSOR_NAMES)):
            # Média dos valores máximos deste sensor em todos os ciclos
            max_sum = sum(cycle[i] for cycle in self.calibration_max_per_cycle)
            self.sensor_max_values[i] = max_sum / num_cycles
            
            # Média dos valores mínimos deste sensor em todos os ciclos
            min_sum = sum(cycle[i] for cycle in self.calibration_min_per_cycle)
            self.sensor_min_values[i] = min_sum / num_cycles
            
            # Threshold é o ponto médio entre max e min
            self.sensor_threshold[i] = (self.sensor_max_values[i] + self.sensor_min_values[i]) / 2.0
        
        print("\n" + "="*60)
        print("CALIBRAÇÃO CONCLUÍDA - Valores Calculados:")
        print("="*60)
        for i, name in enumerate(SENSOR_NAMES):
            print(f"{name:15} | Max: {self.sensor_max_values[i]:.3f} | "
                  f"Min: {self.sensor_min_values[i]:.3f} | "
                  f"Threshold: {self.sensor_threshold[i]:.3f}")
        print("="*60 + "\n")
        
        self.show_calibration_results()

    def show_calibration_results(self):
        """Mostra os resultados da calibração"""
        self.clear_screen()
        
        container = tk.Frame(self.root, bg='#f0f4f8')
        container.pack(expand=True, fill='both', padx=40, pady=40)
        
        success_label = tk.Label(container, text="✓ Calibração Concluída!",
                                font=("Helvetica", 36, "bold"), bg='#f0f4f8', fg='#10b981')
        success_label.pack(pady=20)
        
        info_label = tk.Label(container, text="Valores de calibração calculados com sucesso",
                             font=("Helvetica", 16), bg='#f0f4f8', fg='#4a5568')
        info_label.pack(pady=10)
        
        # Mostrar alguns valores de exemplo
        results_frame = tk.Frame(container, bg='white', relief='raised', borderwidth=2)
        results_frame.pack(pady=30, padx=50, fill='both', expand=True)
        
        results_title = tk.Label(results_frame, text="Exemplo de Valores Calibrados",
                                font=("Helvetica", 18, "bold"), bg='white')
        results_title.pack(pady=15)
        
        # Criar canvas com scrollbar para mostrar todos os sensores
        canvas = tk.Canvas(results_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=canvas.yview)
        results_inner = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=results_inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        # Mostrar valores de todos os sensores
        for i, name in enumerate(SENSOR_NAMES):
            sensor_frame = tk.Frame(results_inner, bg='#f8fafc', relief='groove', borderwidth=1)
            sensor_frame.pack(fill='x', padx=10, pady=5)
            
            name_label = tk.Label(sensor_frame, text=f"{name}:", 
                                 font=("Courier", 11, "bold"), bg='#f8fafc', anchor='w', width=20)
            name_label.pack(side='left', padx=10, pady=8)
            
            values_text = f"Max: {self.sensor_max_values[i]:.3f}  |  Min: {self.sensor_min_values[i]:.3f}  |  Threshold: {self.sensor_threshold[i]:.3f}"
            values_label = tk.Label(sensor_frame, text=values_text,
                                   font=("Courier", 10), bg='#f8fafc', anchor='w')
            values_label.pack(side='left', padx=10, pady=8)
        
        results_inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        
        continue_btn = tk.Button(container, text="Iniciar Detecção de Gestos →",
                                font=("Helvetica", 14, "bold"), bg='#3b82f6', fg='white',
                                activebackground='#2563eb', padx=40, pady=15,
                                cursor='hand2', command=self.start_feedback_screen)
        continue_btn.pack(pady=20)

    def start_feedback_screen(self):
        self.clear_screen()
        self.feedback_active = True
        
        container = tk.Frame(self.root, bg='#f0f4f8')
        container.pack(expand=True, fill='both', padx=20, pady=20)
        
        title_frame = tk.Frame(container, bg='white', relief='raised', borderwidth=2)
        title_frame.pack(fill='x', pady=(0, 20))
        
        title = tk.Label(title_frame, text="Detecção de Gestos em Tempo Real",
                        font=("Helvetica", 22, "bold"), bg='white', fg='#1a202c')
        title.pack(pady=15)
        
        main_layout = tk.Frame(container, bg='#f0f4f8')
        main_layout.pack(expand=True, fill='both')
        
        # Coluna esquerda - Imagem do gesto
        left_col = tk.Frame(main_layout, bg='white', relief='raised', borderwidth=2)
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        gesture_title = tk.Label(left_col, text="Gesto Detectado",
                                font=("Helvetica", 18, "bold"), bg='white', fg='#1a202c')
        gesture_title.pack(pady=15)
        
        self.image_label = tk.Label(left_col, bg='white')
        self.image_label.pack(pady=20, expand=True)
        
        self.gesture_id_label = tk.Label(left_col, text="Gesto: -",
                                        font=("Helvetica", 24, "bold"), bg='white', fg='#3b82f6')
        self.gesture_id_label.pack(pady=15)
        
        # Coluna direita - Valores dos sensores
        right_col = tk.Frame(main_layout, bg='white', relief='raised', borderwidth=2)
        right_col.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        sensor_title = tk.Label(right_col, text="Estado dos Sensores",
                               font=("Helvetica", 16, "bold"), bg='white')
        sensor_title.pack(pady=10)
        
        legend_frame = tk.Frame(right_col, bg='#f0f4f8', relief='flat')
        legend_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(legend_frame, text="🟢 Aberto (< threshold)  |  🔴 Fechado (≥ threshold)",
                font=("Helvetica", 10), bg='#f0f4f8').pack()
        
        sensor_canvas = tk.Canvas(right_col, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_col, orient='vertical', command=sensor_canvas.yview)
        sensor_frame = tk.Frame(sensor_canvas, bg='white')
        
        sensor_canvas.create_window((0, 0), window=sensor_frame, anchor='nw')
        sensor_canvas.configure(yscrollcommand=scrollbar.set)
        
        sensor_canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        self.sensor_labels = []
        self.sensor_state_labels = []
        
        for i, name in enumerate(SENSOR_NAMES):
            frame = tk.Frame(sensor_frame, bg='white')
            frame.pack(fill='x', pady=3, padx=5)
            
            label = tk.Label(frame, text=f"{name}: -",
                           font=("Courier", 10), bg='white', anchor='w', width=35)
            label.pack(side='left')
            
            state_label = tk.Label(frame, text="⚪",
                                  font=("Helvetica", 14), bg='white', width=3)
            state_label.pack(side='left', padx=5)
            
            self.sensor_labels.append(label)
            self.sensor_state_labels.append(state_label)
        
        sensor_frame.update_idletasks()
        sensor_canvas.configure(scrollregion=sensor_canvas.bbox('all'))
        
        finish_btn = tk.Button(container, text="Finalizar Sessão",
                              font=("Helvetica", 14, "bold"), bg='#ef4444', fg='white',
                              activebackground='#dc2626', padx=30, pady=12,
                              cursor='hand2', command=self.finish_session)
        finish_btn.pack(pady=20)

    def finish_session(self):
        self.feedback_active = False
        messagebox.showinfo("Sessão Finalizada", "Sessão encerrada com sucesso!")
        self.setup_main_screen()

    def process_data(self):
        try:
            while True:
                data_string = self.data_queue.get_nowait()
                data_list = data_string.split(',')
                
                if len(data_list) != len(SENSOR_NAMES) + 1:
                    continue
                
                gesture_id = int(data_list[0])
                sensor_values = [float(v) for v in data_list[1:]]
                
                if self.calibration_active:
                    self.update_calibration_values(sensor_values)
                
                if self.feedback_active:
                    self.update_feedback(gesture_id, sensor_values)
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_data)
    
    def update_calibration_values(self, sensor_values):
        """Atualiza valores máximos e mínimos durante a calibração"""
        if self.current_cycle_max is not None and self.current_cycle_min is not None:
            for i, value in enumerate(sensor_values):
                # Atualizar máximo do ciclo atual
                if value > self.current_cycle_max[i]:
                    self.current_cycle_max[i] = value
                
                # Atualizar mínimo do ciclo atual
                if value < self.current_cycle_min[i]:
                    self.current_cycle_min[i] = value
    
    def update_feedback(self, gesture_id, sensor_values):
        """Atualiza a interface de feedback com gesto e estado dos sensores"""
        # Atualizar imagem do gesto
        image = self.images.get(gesture_id, self.images.get(-1))
        if image:
            self.image_label.config(image=image)
            self.image_label.image = image
        
        # Atualizar ID do gesto
        self.gesture_id_label.config(text=f"Gesto: {gesture_id}")
        
        # Atualizar valores dos sensores e determinar estado (aberto/fechado)
        for i, value in enumerate(sensor_values):
            if i < len(self.sensor_labels):
                # Determinar se está aberto ou fechado baseado no threshold
                if value >= self.sensor_threshold[i]:
                    state = "FECHADO"
                    color = '#ef4444'
                    emoji = "🔴"
                    self.finger_states[i] = True
                else:
                    state = "ABERTO"
                    color = '#10b981'
                    emoji = "🟢"
                    self.finger_states[i] = False
                
                # Mostrar valor, threshold e estado
                text = f"{SENSOR_NAMES[i]}: {value:.3f} (T:{self.sensor_threshold[i]:.3f}) {state}"
                self.sensor_labels[i].config(text=text, fg=color)
                self.sensor_state_labels[i].config(text=emoji)

    def start_connection(self):
        if not self.c_thread or not self.c_thread.is_alive():
            self.c_thread = threading.Thread(
                target=read_from_glove_thread,
                args=(self.data_queue, self.status_queue, PATH_TO_C_EXE, GLOVE_CONNECTION_PORT),
                daemon=True
            )
            self.c_thread.start()
    
    def check_status(self):
        try:
            while True:
                status = self.status_queue.get_nowait()
                
                if status == "connected":
                    self.glove_connected = True
                    self.led_canvas.itemconfig(self.led_indicator, fill='#10b981', outline='#059669')
                    self.status_text.config(text="Conectado", fg='#10b981')
                    if hasattr(self, 'start_calibration_btn'):
                        self.start_calibration_btn.config(state='normal')
                
                elif status == "disconnected" or status.startswith("error"):
                    self.glove_connected = False
                    self.led_canvas.itemconfig(self.led_indicator, fill='#ef4444', outline='#dc2626')
                    self.status_text.config(text="Desconectado", fg='#ef4444')
                    if hasattr(self, 'start_calibration_btn'):
                        self.start_calibration_btn.config(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self.check_status)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_closing(self):
        self.feedback_active = False
        self.calibration_active = False
        self.root.destroy()

# ============================================================
# PONTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(IMAGES_FOLDER):
        print(f"AVISO: A pasta '{IMAGES_FOLDER}' não foi encontrada.")
        print("O sistema funcionará, mas sem imagens de gestos.")
    
    root = tk.Tk()
    app = ClinicalGloveApp(root)
    root.mainloop()


