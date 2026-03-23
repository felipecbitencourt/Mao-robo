import tkinter as tk
from tkinter import ttk

class CycleControl(tk.Frame):
    """
    Mini painel para controle de ciclos de calibração.
    Contém:
      - Spinbox de número de ciclos
      - Tempo por ciclo
      - Barra de progresso
      - Botão iniciar/parar
      - Callback: on_start / on_stop
    """

    def __init__(self, master, bg="#ffffff"):
        super().__init__(master, bg=bg)

        self.bg = bg
        self.running = False

        self.on_start = None
        self.on_stop = None

        self._build_widgets()

    # --------------------------------------------------------
    def _build_widgets(self):

        # ---- linha 1: número de ciclos ----
        row1 = tk.Frame(self, bg=self.bg)
        row1.pack(fill='x', pady=2)

        tk.Label(row1, text="Ciclos:", bg=self.bg).pack(side='left')
        self.spin_cycles = tk.Spinbox(
            row1, from_=1, to=999, width=5,
            bg="white", justify='center'
        )
        self.spin_cycles.pack(side='left', padx=6)

        # ---- linha 2: tempo por ciclo ----
        row2 = tk.Frame(self, bg=self.bg)
        row2.pack(fill='x', pady=2)

        tk.Label(row2, text="Tempo/ciclo (s):", bg=self.bg).pack(side='left')
        self.spin_time = tk.Spinbox(
            row2, from_=1, to=999, width=5,
            bg="white", justify='center'
        )
        self.spin_time.pack(side='left', padx=6)

        # ---- barra de progresso ----
        tk.Label(self, text="Progresso:", bg=self.bg).pack(anchor='w')
        self.progress = ttk.Progressbar(self, length=200, mode='determinate')
        self.progress.pack(fill='x', pady=4)

        # ---- contagem regressiva ----
        self.lbl_count = tk.Label(self, text="Contagem: --", bg=self.bg)
        self.lbl_count.pack(anchor='w', pady=2)

        # ---- botão start/stop ----
        self.btn = tk.Button(self, text="Iniciar", width=12, command=self._toggle)
        self.btn.pack(pady=4)

    # --------------------------------------------------------
    def _toggle(self):
        """Alterna entre iniciar e parar."""
        if not self.running:
            self.start()
        else:
            self.stop()

    # --------------------------------------------------------
    def start(self):
        """Coloca widget em modo ativo."""
        self.running = True
        self._set_controls_state(disabled=True)
        self.btn.config(text="Parar")

        if callable(self.on_start):
            self.on_start()

    # --------------------------------------------------------
    def stop(self):
        """Interrompe execução."""
        self.running = False
        self._set_controls_state(disabled=False)
        self.btn.config(text="Iniciar")
        self.progress['value'] = 0
        self.lbl_count.config(text="Contagem: --")

        if callable(self.on_stop):
            self.on_stop()

    # --------------------------------------------------------
    def _set_controls_state(self, disabled=True):
        state = "disabled" if disabled else "normal"
        self.spin_cycles.config(state=state)
        self.spin_time.config(state=state)

    # --------------------------------------------------------
    def get_total_cycles(self):
        return int(self.spin_cycles.get())

    def get_cycle_time(self):
        return float(self.spin_time.get())

    # --------------------------------------------------------
    def update_progress(self, percent):
        """percent: float → 0.0 a 1.0"""
        v = max(0, min(1, percent))
        self.progress['value'] = v * 100

    # --------------------------------------------------------
    def set_countdown(self, seconds):
        """Atualiza texto da contagem regressiva."""
        self.lbl_count.config(text=f"Contagem: {seconds:.1f}s")
