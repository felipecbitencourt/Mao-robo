import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

# --- Cores do Tema Escuro ---
BG_COLOR = "#1a1a2e"
BG_SECONDARY = "#16213e"
ACCENT_COLOR = "#0f3460"
BUTTON_PRIMARY = "#e94560"
BUTTON_SECONDARY = "#0f3460"
TEXT_COLOR = "#eaeaea"
TEXT_MUTED = "#a0a0a0"

def get_script_path(script_name):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), script_name)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

def run_script(script_name):
    target = get_script_path(script_name)
    if not os.path.exists(target):
        target = script_name
    print(f"Iniciando: {target}")
    try:
        subprocess.Popen(['python', target], shell=True)
    except Exception as e:
        messagebox.showerror("Erro", f"Nao foi possivel iniciar {script_name}\n\n{str(e)}")

# --- Janela Principal ---
root = tk.Tk()
root.title("Mão Robótica")
root.geometry("450x380")
root.configure(bg=BG_COLOR)
root.resizable(True, True)

# Centralizar na tela
root.update_idletasks()
width = root.winfo_width()
height = root.winfo_height()
x = (root.winfo_screenwidth() // 2) - (width // 2)
y = (root.winfo_screenheight() // 2) - (height // 2)
root.geometry(f'+{x}+{y}')

# --- Estilo ---
style = ttk.Style()
style.theme_use('clam')

# Configurar estilo dos botoes
style.configure('Primary.TButton',
    font=('Segoe UI', 12, 'bold'),
    padding=(20, 15),
    background=BUTTON_PRIMARY,
    foreground='white',
    borderwidth=0)
style.map('Primary.TButton',
    background=[('active', '#ff6b6b'), ('pressed', '#c53b50')])

style.configure('Secondary.TButton',
    font=('Segoe UI', 11),
    padding=(20, 12),
    background=BUTTON_SECONDARY,
    foreground='white',
    borderwidth=0)
style.map('Secondary.TButton',
    background=[('active', '#1a4a7a'), ('pressed', '#0a2a4a')])

# --- Header ---
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill='x', pady=(40, 20))

# Icone/Emoji de mao
icon_label = tk.Label(header_frame, text="🤖", font=('Segoe UI Emoji', 36), bg=BG_COLOR)
icon_label.pack()

# Titulo
title_label = tk.Label(header_frame, 
    text="Mão Robótica",
    font=('Segoe UI', 24, 'bold'),
    bg=BG_COLOR,
    fg=TEXT_COLOR)
title_label.pack(pady=(10, 0))

# Subtitulo
subtitle_label = tk.Label(header_frame,
    text="Sistema de Controle por Gestos",
    font=('Segoe UI', 10),
    bg=BG_COLOR,
    fg=TEXT_MUTED)
subtitle_label.pack()

# --- Botoes ---
button_frame = tk.Frame(root, bg=BG_COLOR)
button_frame.pack(fill='both', expand=True, padx=50, pady=20)

# Botao Principal
btn_main = ttk.Button(button_frame, 
    text="▶  Iniciar Controle",
    style='Primary.TButton',
    command=lambda: run_script("main.py"))
btn_main.pack(fill='x', pady=10)

# Botao Secundario
btn_test = ttk.Button(button_frame,
    text="🔧  Testar Servos",
    style='Secondary.TButton',
    command=lambda: run_script("testar-dedos.py"))
btn_test.pack(fill='x', pady=10)

# --- Footer ---
footer_frame = tk.Frame(root, bg=BG_COLOR)
footer_frame.pack(side='bottom', fill='x', pady=15)

version_label = tk.Label(footer_frame,
    text="v3.0  •  Feito com ❤️",
    font=('Segoe UI', 9),
    bg=BG_COLOR,
    fg=TEXT_MUTED)
version_label.pack()

# --- Loop Principal ---
root.mainloop()
