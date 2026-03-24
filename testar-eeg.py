import serial.tools.list_ports
import time
from eeg_brainlink import BrainLinkEEG, BrainLinkData

def scan_and_test_eeg():
    print("============================================================")
    print("🔍 TESTE DE CONEXÃO EEG BRAINLINK")
    print("============================================================")
    
    ports = serial.tools.list_ports.comports()
    bluetooth_ports = [p.device for p in ports if "bluetooth" in p.description.lower() or "link" in p.description.lower()]
    
    if not bluetooth_ports:
        print("⚠️ Nenhuma porta Bluetooth detectada. Verifique se o EEG está pareado.")
        # Se não houver, tenta todas as que não parecem ser o Arduino
        bluetooth_ports = [p.device for p in ports if "usb" not in p.description.lower()]

    print(f"Portas candidatas: {bluetooth_ports}")

    for port in bluetooth_ports:
        print(f"\nTentando conectar em {port}...")
        try:
            eeg = BrainLinkEEG(port=port, baudrate=57600)
            if eeg.connect():
                print(f"✅ SUCESSO! Conectado em {port}")
                print("Lendo dados por 10 segundos (coloque o sensor na testa)...")
                
                def print_data(data: BrainLinkData):
                    print(f"  > ATT: {data.attention:3d} | MED: {data.meditation:3d} | SIG: {data.signal:3d} | BATT: {data.battery}%")
                
                eeg.add_callback(print_data)
                
                start_time = time.time()
                while time.time() - start_time < 10:
                    eeg.read_once()
                    time.sleep(0.05)
                
                eeg.disconnect()
                print("\n✅ Teste finalizado com sucesso!")
                return
            else:
                print(f"❌ Falha no handshake em {port}")
        except Exception as e:
            print(f"❌ Erro em {port}: {str(e)}")
    
    print("\n❌ Não foi possível encontrar o BrainLink em nenhuma porta.")

if __name__ == "__main__":
    scan_and_test_eeg()
