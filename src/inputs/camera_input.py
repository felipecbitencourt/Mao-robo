import sys
import cv2
from PySide6.QtCore import QThread, Signal
import time

class CameraInput(QThread):
    frame_signal = Signal(object)  # Emite o frame do OpenCV

    @staticmethod
    def _cv_backend(backend_name):
        """OpenCV: DirectShow (padrão no Windows) ou Media Foundation."""
        if not backend_name:
            backend_name = "dshow"
        b = str(backend_name).lower()
        if b == "msmf":
            return cv2.CAP_MSMF
        return cv2.CAP_DSHOW

    @staticmethod
    def _directshow_device_names():
        """
        Nomes amigáveis na mesma ordem dos índices do DirectShow (OpenCV CAP_DSHOW).
        Opcional: requer pygrabber; sem ele, a UI usa só 'Câmera N'.
        """
        if sys.platform != "win32":
            return None
        try:
            from pygrabber.dshow_graph import FilterGraph
            return FilterGraph().get_input_devices()
        except Exception:
            return None

    @staticmethod
    def list_cameras(max_devices=12, backend="dshow"):
        """
        Retorna lista de (índice, rótulo) para câmeras que entregam frames válidos.
        Com DirectShow + pygrabber, o rótulo inclui o nome do dispositivo no Windows
        (ex.: webcam USB vs. dispositivo Intel virtual).
        """
        cap_backend = CameraInput._cv_backend(backend)
        names = CameraInput._directshow_device_names()
        if cap_backend != cv2.CAP_DSHOW:
            names = None
        available = []
        for i in range(max_devices):
            cap = cv2.VideoCapture(i, cap_backend)
            if not cap.isOpened():
                cap.release()
                continue
            usable = False
            for _ in range(2):
                success, frame = cap.read()
                if success and frame is not None and frame.mean() > 1.0:
                    usable = True
                    break
                time.sleep(0.05)
            cap.release()
            if usable:
                if names is not None and i < len(names):
                    label = f"{names[i]} (índice {i})"
                else:
                    label = f"Câmera {i}"
                available.append((i, label))
        return available

    def __init__(self, camera_index=0, backend="dshow"):
        super().__init__()
        self.camera_index = camera_index
        self.backend = backend or "dshow"
        self.running = False

    def run(self):
        be = CameraInput._cv_backend(self.backend)
        self.cap = cv2.VideoCapture(self.camera_index, be)
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
