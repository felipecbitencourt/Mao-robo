"""Desenho da mão com a abertura de cada dedo (o que está indo para os servos)."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

FINGER_KEYS = ["polegar", "indicador", "medio", "anelar", "minimo"]
FINGER_NAMES = ["Polegar", "Indicador", "Médio", "Anelar", "Mínimo"]

# Comprimento relativo de cada dedo (o médio é o maior)
_LENGTHS = [0.56, 0.88, 1.0, 0.88, 0.70]


def normalize_fingers(fingers: dict, source: str) -> list:
    """
    Converte os valores do hub para abertura em % (0 = fechado, 100 = aberto).

    Unidades de origem:
      - dedos longos: ângulo de servo 60..180
      - polegar vindo da câmera: razão 0..100
      - polegar vindo da luva ou do EEG: ângulo 50..130
    """
    src = (source or "").upper()
    thumb_is_ratio = src.startswith("CAMERA") or src.startswith("VISÃO") or src == "FUSION"
    out = []
    for key in FINGER_KEYS:
        v = float(fingers.get(key, 0) or 0)
        if key == "polegar":
            pct = v if thumb_is_ratio else (v - 50.0) / 80.0 * 100.0
        else:
            pct = (v - 60.0) / 120.0 * 100.0
        out.append(int(max(0, min(100, round(pct)))))
    return out


class HandOutputWidget(QWidget):
    """Cinco cápsulas (dedos) sobre uma palma; o preenchimento mostra a abertura."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0, 0, 0, 0, 0]
        self.active = False
        self._track = QColor("#232731")
        self._fill = QColor("#34D1BF")
        self._palm = QColor("#2A2F3A")
        self.setMinimumSize(220, 150)

    def sizeHint(self):
        return QSize(240, 200)

    def set_theme(self, t):
        self._track = QColor(t["track"] if t["name"] == "light" else "#232731")
        self._palm = QColor("#D5D9E0" if t["name"] == "light" else "#2A2F3A")
        self._fill = QColor(t["accent"])
        self.update()

    def set_values(self, values, active=True):
        self.values = [int(max(0, min(100, v))) for v in values[:5]]
        self.active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        w, h = self.width(), self.height()
        finger_w = 30.0
        gap = 10.0
        total_w = 5 * finger_w + 4 * gap
        x0 = (w - total_w) / 2.0
        palm_h = min(64.0, h * 0.32)
        palm_top = h - palm_h
        max_len = palm_top - 6.0

        fill = QColor(self._fill)
        if not self.active:
            fill.setAlpha(110)

        # Dedos primeiro; a palma é desenhada por cima e esconde a base
        r = finger_w / 2
        for i, val in enumerate(self.values):
            length = max_len * _LENGTHS[i]
            if i == 0:
                length *= 0.9
            x = x0 + i * (finger_w + gap)
            top = palm_top - length
            rect = QRectF(x, top, finger_w, length + r + 2)

            path = QPainterPath()
            path.addRoundedRect(rect, r, r)
            p.setBrush(self._track)
            p.drawPath(path)

            fill_h = length * (val / 100.0)
            if fill_h > 0.5:
                p.save()
                p.setClipPath(path)
                p.setBrush(fill)
                p.drawRect(QRectF(x, palm_top - fill_h, finger_w, fill_h + r + 2))
                p.restore()

        palm = QPainterPath()
        palm.addRoundedRect(QRectF(x0 - 10, palm_top, total_w + 20, palm_h), 22, 22)
        p.setBrush(self._palm)
        p.drawPath(palm)
