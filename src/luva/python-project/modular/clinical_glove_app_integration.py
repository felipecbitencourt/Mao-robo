"""
clinical_glove_app_integration.py
Integração completa: ClinicalGloveApp + GloveReaderThread + detecção de porta e diagnóstico.
Compatível com glove_thread.py já adaptado.
"""

import os
import subprocess
import queue
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time

# -------------------------------------------------------------
# IMPORTAÇÃO SEGURO DE PYSERIAL
# -------------------------------------------------------------
try:
    import serial.tools.list_ports as list_ports
except Exception:
    list_ports = None
    print("[AVISO] pyserial não encontrado — detecção automática de portas limitada.")

# -------------------------------------------------------------
# IMPORTAÇÃO DA GLoveReaderThread
# -------------------------------------------------------------
try:
    from core.glove_thread import GloveReaderThread
except Exception as e:
    GloveReaderThread = None
    print("Aviso: não foi possível importar GloveReaderThread:", e)

# -------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# -------------------------------------------------------------
PATH_TO_C_EXE = "./TestGlove64.exe"
DEFAULT_GLOVE_PORT = None

PORT_KEYWORDS = [
    "5dt", "5-dt", "5_dt", "ftdi", "silicon", "usb serial",
    "usb-serial", "usb serial (com"
]


# =============================================================
# FUNÇÕES DE DETECÇÃO DE PORTA
# =============================================================
def list_system_ports():
    ports = []
    if list_ports is not None:
        for p in list_ports.comports():
            ports.append((p.device, p.description))
    return ports


def detect_glove_port(preferred_keywords=None):
    if preferred_keywords is None:
        preferred_keywords = PORT_KEYWORDS

    ports = list_system_ports()
    if not ports:
        return None

    for dev, desc in ports:
        desc_lower = (desc or "").lower()
        for k in preferred_keywords:
            if k in desc_lower:
                return dev

    return None


def ask_user_choose_port(root):
    ports = list_system_ports()
    if not ports:
        messagebox.showwarning("Nenhuma porta detectada",
                               "Nenhuma porta encontrada. Verifique USB+cabo.")
        return None

    choices = [f"{dev} — {desc}" for dev, desc in ports]
    prompt = "Selecione a porta da luva:\n\n" + \
             "\n".join(f"{i+1}. {c}" for i, c in enumerate(choices))

    while True:
        val = simpledialog.askstring("Escolha de porta", prompt, parent=root)
        if val is None:
            return None

        val = val.strip()

        if val.isdigit():
            idx = int(val) - 1
            if 0 <= idx < len(choices):
                return ports[idx][0]
            else:
                messagebox.showerror("Erro", "Número inválido.")
                continue

        for dev, _ in ports:
            if val.lower() == dev.lower():
                return dev

        return val


def test_executable_port(c_exe_path, port, timeout=3):
    if not os.path.exists(c_exe_path):
        return (None, "", f"Executável não encontrado: {c_exe_path}")

    try:
        res = subprocess.run([c_exe_path, port],
                             capture_output=True, text=True, timeout=timeout)
        return (res.returncode, res.stdout, res.stderr)

    except subprocess.TimeoutExpired:
        return (0, "TIMEOUT: processo provavelmente aberto corretamente.", "")

    except Exception as e:
        return (None, "", str(e))


# =============================================================
# APP PRINCIPAL INTEGRADO
# =============================================================
class ClinicalGloveAppIntegrated:
    def __init__(self, root):
        self.root = root
        self.root.title("Clinical Glove App - Integrated")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f4f8")

        self.data_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.c_thread = None
        self.glove_connected = False

        self._build_ui()

        self.glove_port = DEFAULT_GLOVE_PORT or detect_glove_port()

        if not self.glove_port:
            resp = messagebox.askyesno(
                "Porta não detectada",
                "A porta da luva não foi detectada automaticamente.\nDeseja selecionar manualmente?"
            )
            if resp:
                self.glove_port = ask_user_choose_port(self.root)

        self.port_label_var.set(self.glove_port or "Nenhuma")

        self.root.after(200, self.check_status)
        self.root.after(50, self.process_data)

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------
    def _build_ui(self):
        top = tk.Frame(self.root, bg="#f0f4f8")
        top.pack(fill="x", padx=12, pady=8)

        tk.Label(top, text="Porta da luva:", bg="#f0f4f8").pack(side="left")
        self.port_label_var = tk.StringVar(value="Detectando...")
        tk.Label(top, textvariable=self.port_label_var,
                 bg="#f0f4f8", font=("Courier", 11, "bold")).pack(side="left", padx=6)

        tk.Button(top, text="Diagnosticar portas", command=self.on_diag_list_ports).pack(side="right", padx=6)
        tk.Button(top, text="Testar executável", command=self.on_diag_test_exe).pack(side="right", padx=6)
        tk.Button(top, text="Iniciar Conexão", command=self.start_connection).pack(side="right", padx=6)
        tk.Button(top, text="Parar Conexão", command=self.stop_connection).pack(side="right", padx=6)

        status_frame = tk.Frame(self.root, bg="white", relief="groove", borderwidth=1)
        status_frame.pack(fill="both", padx=12, pady=12)

        self.led_canvas = tk.Canvas(status_frame, width=40, height=40, bg="white", highlightthickness=0)
        self.led_canvas.pack(side="left", padx=10, pady=10)
        self.led_indicator = self.led_canvas.create_oval(6, 6, 34, 34, fill="#ef4444", outline="#dc2626")

        self.status_text = tk.Label(status_frame, text="Desconectado",
                                    bg="white", fg="#ef4444",
                                    font=("Helvetica", 12, "bold"))
        self.status_text.pack(side="left", padx=6)

        log_frame = tk.Frame(self.root, bg="#f8fafc")
        log_frame.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(log_frame, text="Log (debug):", bg="#f8fafc").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=12)
        self.log_text.pack(fill="both", expand=True)

    def log(self, *args):
        text = " ".join(str(a) for a in args) + "\n"
        self.log_text.insert("end", text)
        self.log_text.see("end")
        print(text, end="")

    # ----------------------------------------------------------
    # DIAGNÓSTICO DE PORTAS
    # ----------------------------------------------------------
    def on_diag_list_ports(self):
        ports = list_system_ports()
        if not ports:
            messagebox.showinfo("Portas", "Nenhuma porta encontrada.")
            return
        text = "\n".join(f"{dev} — {desc}" for dev, desc in ports)
        messagebox.showinfo("Portas detectadas", text)

    def on_diag_test_exe(self):
        if not os.path.exists(PATH_TO_C_EXE):
            messagebox.showerror("Erro", f"Executável não encontrado: {PATH_TO_C_EXE}")
            return

        port = self.glove_port or simpledialog.askstring("Porta", "Digite a porta (ex: COM3):")
        if not port:
            return

        self.log(f"Testando {PATH_TO_C_EXE} na porta {port}...")
        code, out, err = test_executable_port(PATH_TO_C_EXE, port)

        self.log(f"Return code: {code}\nstdout:\n{out}\nstderr:\n{err}")

    # ----------------------------------------------------------
    # CONEXÃO COM A LUVA
    # ----------------------------------------------------------
    def start_connection(self):

        # ---------- PRINT EXTRA COMO NO ClinicalGloveApp ----------
        print(f"[ClinicalGloveApp] Porta configurada para a luva: {self.glove_port}")
        # ----------------------------------------------------------

        if self.c_thread and self.c_thread.is_alive():
            self.log("Thread já está rodando.")
            return

        if not self.glove_port:
            self.glove_port = ask_user_choose_port(self.root)
            self.port_label_var.set(self.glove_port or "Nenhuma")

        if not self.glove_port:
            messagebox.showwarning("Porta ausente", "Selecione uma porta.")
            return

        if GloveReaderThread is None:
            messagebox.showerror("Erro", "GloveReaderThread não pôde ser importada.")
            return

        self.c_thread = GloveReaderThread(
            output_queue=self.data_queue,
            status_queue=self.status_queue,
            c_exe_path=PATH_TO_C_EXE,
            glove_port=self.glove_port,
            debug=True,
            auto_reconnect=True,
        )

        self.c_thread.start()
        self.log("GloveReaderThread iniciada.")

    def stop_connection(self):
        if not self.c_thread:
            self.log("Nenhuma thread ativa.")
            return

        try:
            self.c_thread.stop()
            self.log("Comando de parada enviado.")
        except Exception as e:
            self.log("Erro ao parar thread:", e)

    # ----------------------------------------------------------
    # MONITORAMENTO DE THREAD
    # ----------------------------------------------------------
    def check_status(self):
        try:
            while True:
                status = self.status_queue.get_nowait()
                self.log("Status recebido:", status)

                if status == "connected":
                    self.glove_connected = True
                    self.led_canvas.itemconfig(
                        self.led_indicator, fill="#10b981", outline="#059669")
                    self.status_text.config(text="Conectado", fg="#10b981")

                elif status == "disconnected":
                    self.glove_connected = False
                    self.led_canvas.itemconfig(
                        self.led_indicator, fill="#ef4444", outline="#dc2626")
                    self.status_text.config(text="Desconectado", fg="#ef4444")

                elif status.startswith("error"):
                    self.glove_connected = False
                    self.led_canvas.itemconfig(
                        self.led_indicator, fill="#ef4444", outline="#dc2626")
                    self.status_text.config(text="Erro na conexão", fg="#ef4444")

        except queue.Empty:
            pass

        finally:
            self.root.after(200, self.check_status)

    # ----------------------------------------------------------
    # PROCESSAMENTO DE DADOS RECEBIDOS
    # ----------------------------------------------------------
    def process_data(self):
        try:
            while True:
                data = self.data_queue.get_nowait()
                self.log("DADOS:", data)

        except queue.Empty:
            pass

        finally:
            self.root.after(50, self.process_data)


# =============================================================
# ENTRY POINT
# =============================================================
def main():
    root = tk.Tk()
    app = ClinicalGloveAppIntegrated(root)
    root.mainloop()


if __name__ == "__main__":
    main()
