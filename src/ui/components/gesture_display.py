import os
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from core.paths import resource_path

class GestureDisplay(QLabel):
    def __init__(self, images_path="src/luva/gesture-images"):
        super().__init__()
        self.images_path = resource_path(images_path)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(250, 250)
        self.setStyleSheet("""
            background-color: #0C0C14;
            border: 1px solid #1E1E34;
            border-radius: 12px;
            color: #505068;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        self.setText("AGUARDANDO\nGESTO")

    def update_gesture(self, gesture_id):
        """Carrega e exibe a imagem correspondente ao gesto_id"""
        if gesture_id == -1:
            self.setText("SEM MÃO")
            self.setPixmap(QPixmap()) # Limpa se nenhuma mão detectada
            return

        # Busca pelo arquivo .png
        img_name = f"{gesture_id}.png"
        img_path = os.path.join(self.images_path, img_name)
        
        if os.path.exists(img_path):
            # print(f"DEBUG GESTURE: Carregando {img_path}")
            pixmap = QPixmap(img_path)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
        else:
            print(f"DEBUG GESTURE: Arquivo NAO encontrado: {img_path}")
            self.setText(f"GESTO {gesture_id}\n(Imagem ausente)")
            self.setPixmap(QPixmap())
