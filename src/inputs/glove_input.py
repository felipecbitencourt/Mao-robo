import subprocess
import sys
import os
import time
from PySide6.QtCore import QThread, Signal

class GloveInput(QThread):
    data_signal = Signal(dict)
    status_signal = Signal(str)

    def __init__(self, exe_path="src/luva/python-project/TestGlove64.exe", port="USB0"):
        super().__init__()
        self.exe_path = os.path.abspath(exe_path)
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
            
            self.process = subprocess.Popen(
                [self.exe_path, self.port],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=working_dir
            )
            
            self.running = True
            self.status_signal.emit("Luva conectada (via ponte C++)")

            while self.running:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    try:
                        gesture_id = int(parts[0])
                        sensors = [float(v) for v in parts[1:]]
                        # Debug log para a luva
                        print(f"DEBUG GLOVE: Gesto {gesture_id} | Sensores: {sensors[:5]}")
                        
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
            self.stop()

    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        self.status_signal.emit("Luva desconectada")
        self.quit()
        # self.wait() # Removido para evitar deadlock se chamado da própria thread
