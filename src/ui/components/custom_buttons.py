from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, accent_color="#E94560"):
        super().__init__(text, parent)
        self._accent_color = accent_color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self._update_style(checked=False)

    def _update_style(self, checked: bool):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(30, 30, 52, 0.85);
                    color: #E0E0FF;
                    border: 1px solid {self._accent_color};
                    border-left: 3px solid {self._accent_color};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    padding-left: 10px;
                    text-align: left;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #6666AA;
                    border: 1px solid #1E1E34;
                    border-left: 3px solid #1E1E34;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    padding-left: 10px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #161624;
                    border: 1px solid #2A2A44;
                    border-left: 3px solid {self._accent_color};
                    color: #AAAACC;
                }}
            """)

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)


class ActionButton(QPushButton):
    """Botão de ação principal (INICIAR/PARAR) com destaque."""
    def __init__(self, text, color="#E94560", parent=None):
        super().__init__(text, parent)
        self._color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}18;
                color: {color};
                border: 1px solid {color}60;
                border-bottom: 2px solid {color};
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {color}30;
                border: 1px solid {color};
                border-bottom: 2px solid {color};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {color}50;
                border-bottom: 1px solid {color};
                padding-top: 12px;
            }}
        """)
