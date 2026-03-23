import serial.tools.list_ports
import serial

def detect_ports():
    print("\n=== Detector de Portas COM ===")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("Nenhuma porta COM encontrada. Verifique se os dispositivos estão conectados.")
        return

    for port in ports:
        print(f"\nDispositivo encontrado: {port.device}")
        print(f"Descrição: {port.description}")
        print(f"Hardware ID: {port.hwid}")
        
    print("\nSugestão:")
    print("1. Desconecte o Arduino e o BrainLink.")
    print("2. Rode este script.")
    print("3. Conecte um dos dispositivos.")
    print("4. Rode este script novamente para ver qual porta apareceu.")

if __name__ == "__main__":
    detect_ports()
