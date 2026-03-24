import tkinter as tk

class LEDIndicator(tk.Frame):
    """
    Indicador visual de status da luva com LED colorido.
    """

    # Mapeamento de estados internos -> cor do LED
    COLORS = {
        "connected": "green",
        "connecting": "yellow",
        "disconnected": "red",
        "error": "orange",
        "error_connection_failed": "orange",
        "error_port_invalid": "orange",
        "error_unknown": "orange",
        "stopped": "red",

        # compatibilidade com versão antiga
        "ok": "green",
        "conectado": "green",   # alias — compatibilidade com código que usa "conectado"
        "active": "yellow",
        "desconectado": "red",
        "erro": "orange",
    }

    def __init__(self, master, label="Status", initial_state="disconnected", **kwargs):
        bg_color = kwargs.get("bg", "#f8fafc")
        super().__init__(master, bg=bg_color)

        self.state = initial_state
        self.label_text = label

        self.canvas = tk.Canvas(
            self, width=20, height=20,
            bg=bg_color, highlightthickness=0
        )
        self.canvas.pack(side="left", padx=(0, 6))

        self.circle = self.canvas.create_oval(
            2, 2, 18, 18,
            fill=self.COLORS.get(self.state, "red"),
            outline=""
        )

        self.label = tk.Label(
            self,
            text=f"{self.label_text}: {self.state.upper()}",
            font=("Helvetica", 10, "bold"),
            bg=bg_color,
            fg="#1a202c"
        )
        self.label.pack(side="left")

    # --------------------------------------------------------
    # API PÚBLICA
    # --------------------------------------------------------

    def set_state(self, state: str):
        """Atualiza o LED visualmente e o texto."""

        # Se for estado desconhecido → vira erro
        fill = self.COLORS.get(state, "red")

        self.state = state
        self.canvas.itemconfig(self.circle, fill=fill)
        self.label.config(text=f"{self.label_text}: {state.upper()}")

    def get_state(self) -> str:
        return self.state
