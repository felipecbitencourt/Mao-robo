import inspect

if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

from pyfirmata import Arduino,SERVO
import time

board = Arduino('COM5')
pin1 = 10
pin2 = 9
pin3 = 8
pin4 = 7
pin5 = 6

board.digital[pin1].mode = SERVO
board.digital[pin2].mode = SERVO
board.digital[pin3].mode = SERVO
board.digital[pin4].mode = SERVO
board.digital[pin5].mode = SERVO

def rotateServo(pino,angle):
    board.digital[pino].write(angle)
    time.sleep(0.015)

# Valores calibrados para "fechado" de cada dedo (testados manualmente)
VALORES_FECHADOS = {
    10: 150,  # Polegar
    9: 180,   # Indicador
    8: 160,   # Medio
    7: 180,   # Anelar
    6: 130    # Minimo
}

def abrir_fechar(pin, on_off):
    """
    on_off = 1: Abrir (0 graus)
    on_off = 0: Fechar (valor calibrado)
    """
    if on_off == 1:
        rotateServo(pin, 0)
    else:
        valor_fechado = VALORES_FECHADOS.get(pin, 140)
        rotateServo(pin, valor_fechado)

def testeTodos():
    rotateServo(pin1,0)
    rotateServo(pin2,0)
    rotateServo(pin3,0)
    rotateServo(pin4,0)
    rotateServo(pin5,0)
    time.sleep(1)

    rotateServo(pin1,150)
    time.sleep(1)
    rotateServo(pin1,0)
    time.sleep(1)

    rotateServo(pin2,130)
    time.sleep(1)
    rotateServo(pin2,0)
    time.sleep(1)

    rotateServo(pin3,130)
    time.sleep(1)
    rotateServo(pin3,0)
    time.sleep(1)

    rotateServo(pin4,130)
    time.sleep(1)
    rotateServo(pin4,0)
    time.sleep(1)

    rotateServo(pin5,130)
    time.sleep(1)
    rotateServo(pin5,0)
    time.sleep(2)

