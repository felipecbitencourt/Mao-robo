import tkinter as tk
from gui.widgets.led_indicator import LEDIndicator


class MainScreen(tk.Frame):
    """Tela inicial da aplicação."""

    def __init__(self, master, app):
        super().__init__(master, bg="#f0f4f8")
        self.app = app
        self.pack(expand=True, fill="both")
        self.build_ui()

    def build_ui(self):
        # ======================================
        # HEADER COM TÍTULO + LED
        # ======================================
        header = tk.Frame(self, bg="#f0f4f8")
        header.pack(fill="x", pady=(20, 20))

        title = tk.Label(
            header,
            text="Sistema de Neuroreabilitação - Luva 5DT",
            font=("Helvetica", 20, "bold"),
            bg="#f0f4f8", fg="#1a202c"
        )
        title.pack(side="left", padx=40)

        # LED Indicador
        self.led = LEDIndicator(header, status="desconectado")
        self.led.pack(side="right", padx=40)

        # ======================================
        # MENSAGEM
        # ======================================
        info = tk.Label(
            self,
            text="Conecte a luva e selecione uma das opções abaixo.",
            font=("Helvetica", 13),
            bg="#f0f4f8",
            fg="#374151"
        )
        info.pack(pady=(10, 20))

        # ======================================
        # BOTÕES PRINCIPAIS
        # ======================================
        btn_frame = tk.Frame(self, bg="#f0f4f8")
        btn_frame.pack(pady=10)

        # --- BOTÃO CALIBRAÇÃO ---
        calib_btn = tk.Button(
            btn_frame, text="Iniciar Calibração",
            font=("Helvetica", 14, "bold"),
            bg="#3B82F6", fg="white",
            padx=30, pady=12,
            width=20,
            command=self.app.show_calibration_screen
        )
        calib_btn.grid(row=0, column=0, pady=10)

        # --- BOTÃO FEEDBACK EM TEMPO REAL ---
        feedback_btn = tk.Button(
            btn_frame, text="Feedback em Tempo Real",
            font=("Helvetica", 14, "bold"),
            bg="#10B981", fg="white",
            padx=30, pady=12,
            width=20,
            command=self.app.show_feedback_screen
        )
        feedback_btn.grid(row=1, column=0, pady=10)

        # --- BOTÃO HISTÓRICO / RESULTADOS ---
        history_btn = tk.Button(
            btn_frame, text="Histórico de Sessões",
            font=("Helvetica", 14, "bold"),
            bg="#6366F1", fg="white",
            padx=30, pady=12,
            width=20,
            command=self.app.show_history_screen
        )
        history_btn.grid(row=2, column=0, pady=10)
        


        # ======================================
        # BOTÃO DE SAIR
        # ======================================
        exit_btn = tk.Button(
            self, text="Sair",
            font=("Helvetica", 12, "bold"),
            bg="#EF4444", fg="white",
            padx=20, pady=8,
            command=self.app.on_close
        )
        exit_btn.pack(pady=20)

    # ======================================
    # MÉTODO CHAMADO PELO APP
    # ======================================

    def update_glove_status(self, status: str):
        status = status.strip().lower()

        if status in ("connected", "ok"):
            self.led.set_state("ok")
        elif status in ("connecting", "active"):
            self.led.set_state("active")
        elif status.startswith("error"):
            self.led.set_state("erro")

    def update_glove_status(self, connected: bool):
        """Atualiza o LED conforme o status da conexão."""
        # usar estados compatíveis com LEDIndicator (usar "ok" para conectado)
        if connected:
            self.led.set_state("ok")

        else:
            self.led.set_state("desconectado")

