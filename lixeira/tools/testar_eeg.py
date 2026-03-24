"""
Script de Teste - Brain-link Pro
Testa diferentes baudrates e mostra dados brutos
"""

import serial
import time
from eeg_brainlink import BrainLinkParser, BrainLinkData

def testar_porta(porta, baudrate):
    """Testa uma porta COM com um baudrate específico"""
    print(f"\n{'='*60}")
    print(f"🔍 Testando {porta} @ {baudrate} baud")
    print(f"{'='*60}")
    
    contador_pacotes = 0
    ultimo_attention = -1
    ultimo_meditation = -1
    
    def on_data(data: BrainLinkData):
        nonlocal contador_pacotes, ultimo_attention, ultimo_meditation
        contador_pacotes += 1
        
        # Só mostra se houver mudança
        if data.attention != ultimo_attention or data.meditation != ultimo_meditation:
            print(f"📊 Pacote #{contador_pacotes:3d} | "
                  f"Sinal: {data.signal:3d} | "
                  f"Atenção: {data.attention:3d} | "
                  f"Meditação: {data.meditation:3d} | "
                  f"Bateria: {data.battery}%")
            ultimo_attention = data.attention
            ultimo_meditation = data.meditation
    
    try:
        parser = BrainLinkParser(on_data)
        ser = serial.Serial(porta, baudrate, timeout=1)
        
        print(f"✅ Conectado! Aguardando dados...")
        print(f"⏱️  Testando por 15 segundos...\n")
        
        inicio = time.time()
        bytes_recebidos = 0
        
        while time.time() - inicio < 15:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                bytes_recebidos += len(data)
                parser.parse(data)
            time.sleep(0.01)
        
        ser.close()
        
        print(f"\n📈 Estatísticas:")
        print(f"   Bytes recebidos: {bytes_recebidos}")
        print(f"   Pacotes processados: {contador_pacotes}")
        
        if contador_pacotes > 0 and (ultimo_attention > 0 or ultimo_meditation > 0):
            print(f"✅ SUCESSO! Dados EEG recebidos corretamente.")
            return True
        elif bytes_recebidos > 0:
            print(f"⚠️  Recebendo dados, mas Atenção/Meditação ainda em 0")
            print(f"   Isso pode ser normal nos primeiros segundos.")
            return False
        else:
            print(f"❌ Nenhum dado recebido.")
            return False
            
    except serial.SerialException as e:
        print(f"❌ Erro: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  Teste interrompido")
        return False

def main():
    print("=" * 60)
    print("🧠 TESTE DE CONEXÃO BRAIN-LINK PRO")
    print("=" * 60)
    print("\nEste script testará diferentes configurações para")
    print("encontrar a melhor conexão com seu Brain-link Pro.")
    print("\nCertifique-se de que:")
    print("  ✓ O Brain-link Pro está ligado")
    print("  ✓ Pareado via Bluetooth")
    print("  ✓ Sensores na testa (para dados de Atenção/Meditação)")
    
    input("\n▶️  Pressione ENTER para começar...")
    
    # Testa COM5 e COM6 com diferentes baudrates
    portas = ['COM5', 'COM6']
    baudrates = [57600, 115200]
    
    melhor_config = None
    
    for porta in portas:
        for baudrate in baudrates:
            sucesso = testar_porta(porta, baudrate)
            if sucesso:
                melhor_config = (porta, baudrate)
                print(f"\n🎯 Configuração ideal encontrada: {porta} @ {baudrate}")
                break
        if melhor_config:
            break
    
    if melhor_config:
        print(f"\n{'='*60}")
        print(f"✅ CONFIGURAÇÃO RECOMENDADA")
        print(f"{'='*60}")
        print(f"Porta: {melhor_config[0]}")
        print(f"Baudrate: {melhor_config[1]}")
        print(f"\nPróximos passos:")
        print(f"  1. Edite os arquivos Python e use:")
        print(f"     PORTA_COM_EEG = '{melhor_config[0]}'")
        print(f"     BAUDRATE = {melhor_config[1]}")
        print(f"  2. Execute: python calibrar_eeg.py")
    else:
        print(f"\n{'='*60}")
        print(f"⚠️  DIAGNÓSTICO")
        print(f"{'='*60}")
        print(f"Possíveis problemas:")
        print(f"  1. Brain-link Pro não está bem posicionado")
        print(f"     → Ajuste os sensores na testa")
        print(f"  2. Dispositivo precisa de mais tempo")
        print(f"     → Aguarde 30-60 segundos após ligar")
        print(f"  3. Porta COM incorreta")
        print(f"     → Verifique no Gerenciador de Dispositivos")
        print(f"  4. Bateria baixa")
        print(f"     → Carregue o dispositivo")

if __name__ == "__main__":
    main()
