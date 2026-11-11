import csv
import os
import threading
import time
from datetime import datetime

from processing.finger_scale import FINGERS


class CsvRecorder:
    """Grava cada predição despachada pelo hub numa linha de CSV."""

    COLUMNS = ["timestamp", "fonte", "gesto_id", "gesto", "confianca"] + [f"abertura_{f}" for f in FINGERS]

    def __init__(self, directory):
        self.directory = directory
        self.path = None
        self._file = None
        self._writer = None
        self._lock = threading.Lock()

    @property
    def active(self):
        return self._file is not None

    def start(self):
        with self._lock:
            if self._file:
                return self.path
            os.makedirs(self.directory, exist_ok=True)
            name = datetime.now().strftime("sessao_%Y%m%d_%H%M%S.csv")
            self.path = os.path.join(self.directory, name)
            self._file = open(self.path, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow(self.COLUMNS)
            return self.path

    def write(self, data):
        with self._lock:
            if not self._writer:
                return
            opening = data.get("opening") or {}
            self._writer.writerow(
                [f"{data.get('timestamp') or time.time():.3f}", data.get("source", ""),
                 data.get("gesture_id", -1), data.get("prediction", ""), data.get("confidence", "")]
                + [("" if f not in opening else f"{opening[f]:.3f}") for f in FINGERS]
            )

    def stop(self):
        with self._lock:
            if self._file:
                self._file.close()
            self._file = None
            self._writer = None
            return self.path
