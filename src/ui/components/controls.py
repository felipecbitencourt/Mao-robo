"""Controles reutilizáveis do novo visual: cartões, chips, abas segmentadas e chave liga/desliga."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from ui.theme import repolish


def card(padding=18, spacing=12, horizontal=False):
    """Cartão com fundo de superfície; devolve (frame, layout)."""
    frame = QFrame()
    frame.setProperty("card", True)
    layout = QHBoxLayout(frame) if horizontal else QVBoxLayout(frame)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(spacing)
    return frame, layout


def label(text="", name=None, role=None, wrap=False):
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    if role:
        lbl.setProperty("role", role)
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def divider():
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.NoFrame)
    return line


class StatusChip(QLabel):
    """Etiqueta de status com bolinha colorida (ok / warn / danger / off / mono)."""

    _DOT = {"ok": "accent", "warn": "warn", "danger": "danger", "off": "text_faint"}

    def __init__(self, text="", level="off", parent=None):
        super().__init__(parent)
        self.setProperty("chip", True)
        self.setTextFormat(Qt.RichText)
        self._text = text
        self._level = level
        self._theme = None
        self.set_state(level, text)

    def set_theme(self, theme):
        self._theme = theme
        self._render()

    def set_state(self, level, text):
        changed = level != self._level
        self._level = level
        self._text = text
        self.setProperty("level", level)
        if changed:
            repolish(self)
        self._render()

    def _render(self):
        key = self._DOT.get(self._level)
        if key and self._theme:
            dot = f'<span style="color:{self._theme[key]};">●</span>&nbsp;&nbsp;'
        else:
            dot = ""
        self.setText(f"{dot}{self._text}")


class Segmented(QFrame):
    """Grupo de botões exclusivos com cara de abas segmentadas."""

    def __init__(self, labels, size=None, accent=False, exclusive=True, parent=None):
        super().__init__(parent)
        self.setProperty("segmented", True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)
        self.group = QButtonGroup(self)
        self.group.setExclusive(exclusive)
        self.buttons = []
        for i, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("seg", True)
            if size:
                btn.setProperty("size", size)
            if accent:
                btn.setProperty("accent", True)
            self.group.addButton(btn, i)
            layout.addWidget(btn)
            self.buttons.append(btn)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_current(self, index):
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)


class ToggleSwitch(QAbstractButton):
    """Chave liga/desliga desenhada à mão (checkable)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 26)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)
        self._colors = {"on": "#34D1BF", "off": "#2A2F3A", "knob_on": "#0F1115", "knob_off": "#9AA3B2"}

    def set_theme(self, t):
        self._colors = {
            "on": t["accent"], "off": t["track"] if t["name"] == "light" else t["raised"],
            "knob_on": t["accent_on"], "knob_off": t["text_muted"] if t["name"] == "dark" else "#FFFFFF",
        }
        self.update()

    def sizeHint(self):
        return QSize(44, 26)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _get_knob(self):
        return self._pos

    def _set_knob(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        on = QColor(self._colors["on"])
        off = QColor(self._colors["off"])
        mix = lambda a, b, k: int(a + (b - a) * k)
        track = QColor(mix(off.red(), on.red(), self._pos), mix(off.green(), on.green(), self._pos),
                       mix(off.blue(), on.blue(), self._pos))
        if not self.isEnabled():
            track.setAlpha(110)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 13, 13)
        p.setBrush(QColor(self._colors["knob_on"] if self._pos > 0.5 else self._colors["knob_off"]))
        x = 4 + self._pos * (self.width() - 26)
        p.drawEllipse(QRectF(x, 4, 18, 18))


class SwitchRow(QWidget):
    """Linha com título, descrição e uma ToggleSwitch à direita."""

    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(52)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 6, 0, 6)
        row.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:14px; font-weight:500;")
        self.subtitle = label(subtitle, name="caption")
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)
        row.addLayout(texts, 1)
        self.switch = ToggleSwitch()
        row.addWidget(self.switch, 0, Qt.AlignVCenter)

    def mousePressEvent(self, event):
        if self.switch.isEnabled():
            self.switch.toggle()
        super().mousePressEvent(event)
