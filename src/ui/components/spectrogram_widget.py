from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient
from collections import deque

class SpectrogramWidget(QWidget):
    """
    Widget de Espectrograma em Tempo Real (Heatmap)
    Visualiza as 8 bandas de frequência do EEG como um mapa de calor temporal.
    """
    def __init__(self, parent=None, max_columns=80):
        super().__init__(parent)
        self.max_columns = max_columns
        # Lista das 8 bandas na ordem de exibição (de baixo para cima em frequência)
        self.band_keys = [
            "delta", "theta", "low_alpha", "high_alpha", 
            "low_beta", "high_beta", "low_gamma", "high_gamma"
        ]
        self.band_labels = [
            "Δ Delta", "θ Theta", "α Low", "α High", 
            "β Low", "β High", "γ Low", "γ High"
        ]
        
        # Buffer de dados: cada entrada é um dicionário com as 8 bandas
        self.buffer = deque(maxlen=self.max_columns)
        
        # Escala automática (opcional) ou fixa? 
        # BrainLink costuma enviar valores em escalas arbitrárias, vamos tentar normalizar.
        self.max_observed = 1000  # Valor base para normalização (ajustável)

        self.setMinimumHeight(200)
        self._bg = QColor("#0A0C10")
        self._label = QColor("#9AA3B2")
        self._axis = QColor("#353B47")

    def add_data(self, waves_dict):
        """Adiciona um novo conjunto de 8 bandas ao buffer e solicita repaint"""
        if not waves_dict:
            return
            
        # Extrai apenas as bandas que nos interessam
        entry = [waves_dict.get(key, 0) for key in self.band_keys]
        
        # Atualiza o valor máximo observado para normalização dinâmica (com decaimento)
        current_max = max(entry) if entry else 0
        if current_max > self.max_observed:
            self.max_observed = current_max
        else:
            # Decaimento lento para não ficar travado em um pico antigo
            self.max_observed = max(500, self.max_observed * 0.999)
            
        self.buffer.append(entry)
        self.update()

    # Paleta perceptual (estilo viridis): escura → verde-água → amarela
    _STOPS = [
        (0.00, (13, 8, 40)), (0.25, (59, 46, 120)), (0.50, (33, 145, 140)),
        (0.75, (94, 201, 98)), (1.00, (253, 231, 37)),
    ]

    def set_theme(self, t):
        self._bg = QColor(t["video_bg"] if t["name"] == "dark" else t["surface_alt"])
        self._label = QColor(t["text_muted"])
        self._axis = QColor(t["border_strong"])
        self.update()

    def _get_color(self, value):
        """Mapeia um valor normalizado (0-1) para a paleta perceptual"""
        v = max(0.0, min(1.0, value))
        for (p0, c0), (p1, c1) in zip(self._STOPS, self._STOPS[1:]):
            if v <= p1:
                k = (v - p0) / (p1 - p0)
                return QColor(*[int(a + (b - a) * k) for a, b in zip(c0, c1)])
        return QColor(*self._STOPS[-1][1])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Margens para labels
        label_width = 60
        margin_bottom = 20
        draw_w = w - label_width
        draw_h = h - margin_bottom
        
        if not self.buffer:
            painter.setPen(self._label)
            painter.drawText(self.rect(), Qt.AlignCenter, "Aguardando sinal do EEG…")
            return

        # Desenha o fundo
        painter.fillRect(label_width, 0, draw_w, draw_h, self._bg)

        num_bands = len(self.band_keys)
        cell_h = draw_h / num_bands
        cell_w = draw_w / self.max_columns

        # Inverte a ordem das bandas para desenhar de cima para baixo (Gamma no topo)
        for row_idx, band_data_idx in enumerate(reversed(range(num_bands))):
            y = row_idx * cell_h
            
            # Label da banda
            painter.setPen(self._label)
            font = painter.font()
            font.setPointSize(8)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(QRectF(5, y, label_width - 10, cell_h), Qt.AlignRight | Qt.AlignCenter, self.band_labels[band_data_idx])

            # Dados (buffer)
            for col_idx, entry in enumerate(self.buffer):
                val = entry[band_data_idx]
                norm_val = val / max(1, self.max_observed)
                
                # Ajuste logarítmico simples para melhor contraste visual
                import math
                if norm_val > 0:
                    norm_val = math.log10(1 + norm_val * 9) # Transforma 0-1 em 0-1 mais sensível
                
                color = self._get_color(norm_val)
                x = label_width + col_idx * cell_w
                painter.fillRect(QRectF(x, y, cell_w + 1, cell_h + 1), color)

        # Desenha régua temporal (simples)
        painter.setPen(self._axis)
        painter.drawLine(label_width, draw_h, w, draw_h)
        painter.drawText(QRectF(label_width, draw_h + 2, draw_w, 18), Qt.AlignLeft, "antes")
        painter.drawText(QRectF(label_width, draw_h + 2, draw_w, 18), Qt.AlignRight, "agora")
