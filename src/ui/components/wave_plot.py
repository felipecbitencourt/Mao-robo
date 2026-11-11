from collections import deque

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class WavePlotWidget(QWidget):
    """
    Gráfico de linha 0–100 com rolagem. Aceita várias séries no mesmo
    eixo e uma linha de limiar opcional (tracejada).
    """

    def __init__(self, color_str="#34D1BF", parent=None, length=300):
        super().__init__(parent)
        self.length = length
        self.series = {"default": {"color": QColor(color_str), "data": deque([0] * length, maxlen=length)}}
        self.threshold = None
        self.bg_col = QColor(0, 0, 0, 0)
        self.grid_col = QColor("#262A33")
        self.threshold_col = QColor("#9AA3B2")
        self.setMinimumHeight(80)

    # API antiga (uma série)
    def add_value(self, val):
        self.add_series_value("default", val)

    def add_series(self, key, color_str):
        if "default" in self.series and len(self.series) == 1 and key != "default":
            self.series.pop("default")
        self.series[key] = {"color": QColor(color_str), "data": deque([0] * self.length, maxlen=self.length)}

    def set_series_color(self, key, color_str):
        if key in self.series:
            self.series[key]["color"] = QColor(color_str)
            self.update()

    def add_series_value(self, key, val):
        if key in self.series:
            self.series[key]["data"].append(max(0, min(100, val)))
            self.update()

    def set_threshold(self, value):
        self.threshold = value
        self.update()

    def update_theme(self, bg_str, grid_str, threshold_str=None):
        self.bg_col = QColor(bg_str)
        self.grid_col = QColor(grid_str)
        if threshold_str:
            self.threshold_col = QColor(threshold_str)
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.bg_col.alpha() > 0:
            p.fillRect(self.rect(), self.bg_col)

        pad = 4.0
        y_of = lambda v: pad + (h - 2 * pad) * (1 - v / 100.0)

        p.setPen(QPen(self.grid_col, 1))
        for v in (0, 25, 50, 75, 100):
            y = y_of(v)
            p.drawLine(QPointF(0, y), QPointF(w, y))

        if self.threshold is not None:
            ty = y_of(self.threshold)
            band = QColor(self.threshold_col)
            band.setAlpha(18)
            p.fillRect(0, 0, w, int(ty), band)
            pen = QPen(self.threshold_col, 1.5, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(0, ty), QPointF(w, ty))

        for s in self.series.values():
            data = s["data"]
            n = len(data)
            if n < 2:
                continue
            dx = w / (n - 1)
            path = QPainterPath(QPointF(0, y_of(data[0])))
            for i in range(1, n):
                path.lineTo(QPointF(i * dx, y_of(data[i])))
            p.setPen(QPen(s["color"], 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
