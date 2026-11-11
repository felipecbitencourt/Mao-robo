from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
import cv2


class VideoDisplay(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("video")
        self.setAlignment(Qt.AlignCenter)
        self.setText("Aguardando imagem da câmera…")
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_frame(self, frame):
        """Converte frame do OpenCV para QPixmap e exibe no QLabel"""
        if frame is None:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qt_image = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
