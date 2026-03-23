import serial
import time
from PySide6.QtCore import QObject

class ArduinoOutput(QObject):
    def __init__(self, port="COM3", baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            return True
        except:
            return False

    def send_command(self, command):
        """
        Envia comando para o Arduino.
        Ex: command = '1' (abrir), '0' (fechar)
        """
        if self.serial and self.serial.is_open:
            self.serial.write(str(command).encode())
            return True
        return False

    def disconnect(self):
        if self.serial:
            self.serial.close()
