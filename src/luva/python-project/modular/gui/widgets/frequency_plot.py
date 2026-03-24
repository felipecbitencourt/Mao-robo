import tkinter as tk

class FrequencyPlot(tk.Frame):
    """
    Exibe um gráfico de FFT usando Tkinter Canvas.
    Cada atualização redesenha apenas as barras.
    """

    def __init__(self, master, width=350, height=140, bg="#ffffff"):
        super().__init__(master, bg=bg)
        
        self.bg = bg
        self.width = width
        self.height = height
        
        self.canvas = tk.Canvas(
            self, width=width, height=height,
            bg=bg, highlightthickness=0
        )
        self.canvas.pack()

        self.bar_ids = []
        self.n_bins = 0

    # -------------------------------------------------------------
    def update(self, spectrum):
        """
        Recebe lista/array com magnitudes da FFT.
        Normaliza, desenha barras e destaca o pico.
        """
        if len(spectrum) == 0:
            return
        
        self.canvas.delete("bar")  # limpa somente as barras
        
        values = self._normalize(spectrum)
        self._draw_bars(values)

        # pico
        peak_index = max(range(len(values)), key=lambda i: values[i])
        self._highlight_peak(peak_index, values[peak_index])

    # -------------------------------------------------------------
    def _normalize(self, values):
        """Normaliza os valores para 0–1."""
        max_v = max(values)
        return [v / max_v if max_v > 0 else 0 for v in values]

    # -------------------------------------------------------------
    def _draw_bars(self, values):
        """Desenha as barras verticais do espectro."""
        n = len(values)
        bar_width = self.width / max(n, 1)

        for i, v in enumerate(values):
            x0 = i * bar_width
            x1 = x0 + bar_width * 0.9
            y1 = self.height
            y0 = self.height - v * (self.height * 0.9)

            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                fill="#3B82F6", outline="",
                tags="bar"
            )

    # -------------------------------------------------------------
    def _highlight_peak(self, index, value):
        """Redesenha a barra do pico em vermelho."""
        bar_width = self.width / max(1, index + 1)
        x0 = index * bar_width
        x1 = x0 + bar_width * 0.9
        y1 = self.height
        y0 = self.height - value * (self.height * 0.9)

        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#EF4444", outline="",
            tags="bar"
        )
