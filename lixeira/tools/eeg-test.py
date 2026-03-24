import serial

ser = serial.Serial('COM5', 57600, timeout=1)
print("Conectado ao BrainLink!")

while True:
    data = ser.read(32)
    if data:
        print(data)
