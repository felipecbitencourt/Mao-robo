import tkinter as tk
from tkinter import ttk

class SensorList(tk.Frame):
    """
    Widget de lista de sensores.
    Compatível com chamadas antigas que passam:
      - sensor_names (lista de nomes)  OR
      - sensor_values (lista de valores)  <-- usado nas telas
    Suporta:
      - thresholds (opcional) para marcar sensores acima do limite
      - allow_selection (opcional) para permitir ativar/desativar sensores
    """

    def __init__(self, master, sensor_names=None, sensor_values=None,
                 thresholds=None, allow_selection=False,
                 max_value=1.0, bg="#ffffff"):
        super().__init__(master, bg=bg)
        # Determinar nomes a partir de sensor_names ou comprimento de sensor_values
        if sensor_names is None and sensor_values is not None:
            sensor_names = [f"Sensor {i+1}" for i in range(len(sensor_values))]
        elif sensor_names is None:
            sensor_names = []

        self.sensor_names = sensor_names
        self.max_value = max_value if max_value is not None else 1.0
        self.bg = bg
        self.rows = []
        self.thresholds = thresholds
        self.allow_selection = allow_selection

        # Máscara de ativação (True = ativo)
        # Se tiver sensor_values, inicializa ativos; caso contrário todos ativos
        n = len(self.sensor_names)
        self.active_mask = [True] * n

        # Área com scroll
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical',
                                       command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)

        self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        self._build_rows()
        self._update_scroll_region()

    # -----------------------------------------------------------
    def _update_scroll_region(self):
        """Atualiza região do scroll sempre que necessário."""
        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    # -----------------------------------------------------------
    def _build_rows(self):
        BAR_W = 160
        BAR_H = 12

        for idx, name in enumerate(self.sensor_names):
            row_frame = tk.Frame(self.inner, bg=self.bg)
            row_frame.pack(fill='x', pady=4, padx=4)

            # Nome
            lbl = tk.Label(row_frame, text=name, width=12,
                           anchor='w', bg=self.bg)
            lbl.pack(side='left')

            # Barra horizontal
            bar_canvas = tk.Canvas(row_frame, width=BAR_W, height=BAR_H,
                                   bg="#e6e6e6", highlightthickness=0)
            bar_canvas.pack(side='left', padx=6)
            bar_rect = bar_canvas.create_rectangle(0, 0, 1, BAR_H,
                                                   fill="#67a6f7", width=0)

            # Valor numérico
            val_lbl = tk.Label(row_frame, text="0.000", width=6, bg=self.bg)
            val_lbl.pack(side='left', padx=6)

            # Status
            status_lbl = tk.Label(row_frame, text="⚪", width=3, bg=self.bg)
            status_lbl.pack(side='left')

            # Checkbox de seleção (opcional)
            cb_var = None
            cb = None
            if self.allow_selection:
                cb_var = tk.BooleanVar(value=True)
                cb = tk.Checkbutton(row_frame, variable=cb_var, bg=self.bg,
                                    command=self._make_selection_cb(idx, cb_var))
                cb.pack(side='right', padx=4)

            self.rows.append({
                "frame": row_frame,
                "label": lbl,
                "bar": bar_canvas,
                "bar_rect": bar_rect,
                "value": val_lbl,
                "status": status_lbl,
                "checkbox_var": cb_var,
                "checkbox": cb
            })

    def _make_selection_cb(self, idx, var):
        def _cb():
            self.active_mask[idx] = bool(var.get())
        return _cb

    # -----------------------------------------------------------
    def update_values(self, values, thresholds=None, active_mask=None):
        """
        values: lista de valores dos sensores
        thresholds: lista opcional do mesmo tamanho
        active_mask: lista de booleans para ativar/desativar sensores (True = ativo)
        """
        BAR_W = 160

        if thresholds is None:
            thresholds = self.thresholds

        if active_mask is not None:
            # atualizar máscara interna e checkboxes se houver
            self.active_mask = list(active_mask)
            for i, row in enumerate(self.rows):
                cb_var = row.get("checkbox_var")
                if cb_var is not None and i < len(self.active_mask):
                    cb_var.set(bool(self.active_mask[i]))

        for i, row in enumerate(self.rows):
            if i >= len(values):
                continue

            try:
                v = float(values[i])
            except Exception:
                v = 0.0

            row["value"].config(text=f"{v:.3f}")

            # Redimensionamento da barra
            bar_canvas = row["bar"]
            rect = row["bar_rect"]
            fill_w = max(1, min(BAR_W, int((v / self.max_value) * BAR_W))) if self.max_value else 1

            # Lógica de cor / status
            color = "#67a6f7"   # Normal azul

            if i < len(self.active_mask) and not self.active_mask[i]:
                color = "#888888"   # Cinza — desativado
                row["status"].config(text="◼️")
            elif thresholds and i < len(thresholds) and v >= thresholds[i]:
                color = "#ff5b5b"   # Vermelho — acima do limite
                row["status"].config(text="🔴")
            else:
                row["status"].config(text="🟢" if thresholds else "⚪")

            bar_canvas.coords(rect, 0, 0, fill_w, 12)
            bar_canvas.itemconfig(rect, fill=color)

        self._update_scroll_region()

    # -----------------------------------------------------------
    def get_disabled_mask(self):
        """Retorna lista booleana onde True = sensor desabilitado (conforme chamadas existentes)."""
        return [not bool(x) for x in self.active_mask]

    # -----------------------------------------------------------
    def set_thresholds(self, thresholds):
        self.thresholds = thresholds

    # -----------------------------------------------------------
    def set_max_value(self, max_value):
        self.max_value = max_value if max_value is not None else 1.0

    # -----------------------------------------------------------
    def refresh(self):
        """Atualiza a exibição com os valores atuais."""
        values = [row["value"].cget("text") for row in self.rows]
        self.update_values(values)
