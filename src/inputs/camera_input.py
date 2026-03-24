import cv2
from PySide6.QtCore import QThread, Signal
import time

class CameraInput(QThread):
    frame_signal = Signal(object)  # Emite o frame do OpenCV

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.running = True
        while self.running:
            success, frame = self.cap.read()
            if success:
                self.frame_signal.emit(frame)
            time.sleep(0.01)
            
        self.cap.release()

    def stop(self):
        self.running = False
        self.wait()
