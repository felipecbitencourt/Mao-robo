import inspect
import time

# Monkey patch for pyfirmata compatibility
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

from pyfirmata import Arduino, util

PORTA_COM = 'COM5'

print(f"Conectando ao Arduino na porta {PORTA_COM}...")
try:
    board = Arduino(PORTA_COM)
    print("Conexao estabelecida!")
except Exception as e:
    print(f"Erro ao conectar: {e}")
    exit()

# Start iterator to keep serial buffer from overflowing
it = util.Iterator(board)
it.start()

# O LED integrado do Arduino geralmente fica no pino 13
PINO_LED = 13

print(f"Piscando o LED no pino {PINO_LED} para testar comunicacao...")
print("Se o LED 'L' no Arduino piscar, o computador esta controlando a placa corretamente.")

try:
    while True:
        board.digital[PINO_LED].write(1) # Liga LED
        print("LED ON")
        time.sleep(1)
        board.digital[PINO_LED].write(0) # Desliga LED
        print("LED OFF")
        time.sleep(1)
except KeyboardInterrupt:
    board.exit()
    print("Teste finalizado.")
