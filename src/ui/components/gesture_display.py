import os
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from core.paths import resource_path


class GestureDisplay(QLabel):
    """Miniatura ilustrativa do gesto reconhecido."""

    def __init__(self, images_path="src/luva/gesture-images", size=250):
        super().__init__()
        self.images_path = resource_path(images_path)
        self.setObjectName("gesture_img")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(size, size)
        self.setText("Sem gesto")

    def update_gesture(self, gesture_id):
        """Carrega e exibe a imagem correspondente ao gesture_id"""
        if gesture_id == -1:
            self.setPixmap(QPixmap())
            self.setText("Sem mão")
            return

        img_path = os.path.join(self.images_path, f"{gesture_id}.png")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            margin = 8
            scaled = pixmap.scaled(self.width() - margin, self.height() - margin,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
        else:
            if gesture_id != 30:  # Evita log de erro para métricas EEG dinâmicas
                print(f"DEBUG GESTURE: Arquivo NAO encontrado: {img_path}")
            self.setPixmap(QPixmap())
            self.setText("EEG" if gesture_id == 30 else f"#{gesture_id}")
