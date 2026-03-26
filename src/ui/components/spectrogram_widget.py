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

    def _get_color(self, value):
        """Mapeia um valor normalizado (0-1) para uma cor de mapa de calor"""
        # Gradiente: Preto -> Azul -> Verde -> Amarelo -> Vermelho -> Branco
        v = max(0.0, min(1.0, value))
        
        if v < 0.2: # Preto -> Azul
            return QColor(0, 0, int(v / 0.2 * 255))
        elif v < 0.4: # Azul -> Ciano/Verde
            return QColor(0, int((v - 0.2) / 0.2 * 255), 255)
        elif v < 0.6: # Verde -> Amarelo
            return QColor(int((v - 0.4) / 0.2 * 255), 255, 255 - int((v - 0.4) / 0.2 * 255))
        elif v < 0.8: # Amarelo -> Vermelho
            return QColor(255, 255 - int((v - 0.6) / 0.2 * 255), 0)
        else: # Vermelho -> Branco
            return QColor(255, int((v - 0.8) / 0.2 * 255), int((v - 0.8) / 0.2 * 255))

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
            painter.setPen(QColor("#555555"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Aguardando sinal EEG...")
            return

        # Desenha o fundo
        painter.fillRect(label_width, 0, draw_w, draw_h, QColor("#10101A"))

        num_bands = len(self.band_keys)
        cell_h = draw_h / num_bands
        cell_w = draw_w / self.max_columns

        # Inverte a ordem das bandas para desenhar de cima para baixo (Gamma no topo)
        for row_idx, band_data_idx in enumerate(reversed(range(num_bands))):
            y = row_idx * cell_h
            
            # Label da banda
            painter.setPen(QColor("#A7A7C6"))
            font = painter.font()
            font.setPointSize(8)
            font.setBold(True)
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
        painter.setPen(QColor("#3A3A52"))
        painter.drawLine(label_width, draw_h, w, draw_h)
        painter.drawText(QRectF(label_width, draw_h + 2, draw_w, 18), Qt.AlignLeft, "Anterior")
        painter.drawText(QRectF(label_width, draw_h + 2, draw_w, 18), Qt.AlignRight, "Agora")
