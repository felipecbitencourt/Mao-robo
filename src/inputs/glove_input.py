import subprocess
import sys
import os
import time
from PySide6.QtCore import QThread, Signal
from core.paths import resource_path

class GloveInput(QThread):
    data_signal = Signal(dict)
    status_signal = Signal(str)

    def __init__(self, exe_path="src/luva/python-project/TestGlove64.exe", port="USB0"):
        super().__init__()
        self.exe_path = resource_path(exe_path)
        self.port = port
        self.running = False
        self.process = None

    def run(self):
        if not os.path.exists(self.exe_path):
            self.status_signal.emit(f"Erro: Executável não encontrado em {self.exe_path}")
            return

        try:
            # Definir o diretório de trabalho para que o DLL seja encontrado
            working_dir = os.path.dirname(self.exe_path)
            
            # stderr descartado: se fosse um PIPE que ninguém lê, o buffer enche
            # e o executável da luva trava ao escrever nele.
            proc = subprocess.Popen(
                [self.exe_path, self.port],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                cwd=working_dir
            )
            self.process = proc

            self.running = True
            self.status_signal.emit("Luva conectada (via ponte C++)")

            while self.running:
                # Usa a referência local: stop() pode zerar self.process de outra thread
                line = proc.stdout.readline()
                if not line:
                    break
                
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    try:
                        gesture_id = int(parts[0])
                        sensors = [float(v) for v in parts[1:]]
                        self.data_signal.emit({
                            "gesture_id": gesture_id,
                            "sensors": sensors,
                            "timestamp": time.time()
                        })
                    except ValueError:
                        continue

        except Exception as e:
            self.status_signal.emit(f"Erro na luva: {str(e)}")
        finally:
            self._terminate_process()

    def _terminate_process(self):
        proc, self.process = self.process, None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.status_signal.emit("Luva desconectada")

    def stop(self):
        self.running = False
        # Encerrar o processo fecha o stdout e destrava o readline() da thread
        self._terminate_process()
