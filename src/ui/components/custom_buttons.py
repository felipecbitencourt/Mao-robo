"""
Botões legados mantidos por compatibilidade.

O visual agora vem da folha de estilo global (ui/theme.py); estas
classes só marcam a variante certa.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, accent_color=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("variant", "ghost")

    def _update_style(self, checked: bool):
        pass


class ActionButton(QPushButton):
    """Botão de ação principal."""
    def __init__(self, text, color=None, parent=None, variant="primary"):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("variant", variant)
