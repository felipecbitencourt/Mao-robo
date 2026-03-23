from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect, Property, Signal
from PySide6.QtGui import QColor, QPalette

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, accent_color="#e94560"):
        super().__init__(text, parent)
        self._accent_color = accent_color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #0f3460;
                color: white;
                border: 2px solid #0f3460;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #16213e;
                border: 2px solid {self._accent_color};
            }}
        """)

        # Animação de escala (opcional, complexa via QPropertyAnimation em geometria)
        # Mais simples: Animação de cor via StyleSheet ou QPalette
        
    def enterEvent(self, event):
        super().enterEvent(event)
        # Aqui poderíamos disparar uma animação de escala se quiséssemos
        pass

    def leaveEvent(self, event):
        super().leaveEvent(event)
        pass

class ActionButton(AnimatedButton):
    """Botão de ação principal (INICIAR/PARAR) com destaque"""
    def __init__(self, text, color="#e94560", parent=None):
        super().__init__(text, parent, accent_color=color)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }}
            QPushButton:hover {{
                background-color: white;
                color: {color};
                border: 2px solid {color};
            }}
            QPushButton:pressed {{
                background-color: #533440;
                margin-top: 3px;
                margin-left: 3px;
            }}
        """)

from PySide6.QtCore import Qt
