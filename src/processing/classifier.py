import random
import time
from PySide6.QtCore import QObject, Signal

class Classifier(QObject):
    prediction_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        self.running = False

    def process_data(self, camera_frame=None, glove_data=None, eeg_data=None):
        """
        Processa os dados das diversas fontes e retorna a predição.
        Por enquanto, simula o processamento.
        """
        # Simulação de processamento
        states = ["ABERTA", "FECHADA", "PINÇA", "OK", "APONTAR"]
        prediction = random.choice(states)
        confidence = random.randint(70, 99)
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "timestamp": time.time()
        }
