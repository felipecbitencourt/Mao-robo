"""
Controle EEG SIMPLIFICADO - Apenas visualização (SEM Arduino)
Use este para testar o EEG primeiro, antes de conectar o Arduino
"""

import time
from eeg_brainlink import BrainLinkEEG, BrainLinkData

# --- Configurações ---
PORTA_COM_EEG = 'COM6'  # Ajuste conforme sua porta
BAUDRATE = 57600

# Thresholds
THRESHOLD_CONCENTRACAO = 60
THRESHOLD_RELAXAMENTO = 60

class ControleEEGSimples:
    def __init__(self):
        self.eeg = BrainLinkEEG(port=PORTA_COM_EEG, baudrate=BAUDRATE)
        self.estado_atual = 'neutro'
        
    def on_eeg_data(self, data: BrainLinkData):
        """Callback para processar dados EEG"""
        # Determina estado
        if data.signal > 100:
            estado = 'sinal_ruim'
        elif data.attention > THRESHOLD_CONCENTRACAO:
            estado = 'concentrado'
        elif data.meditation > THRESHOLD_RELAXAMENTO:
            estado = 'relaxado'
        else:
            estado = 'neutro'
        
        # Mostra dados
        simbolo = {
            'concentrado': '🤜 FECHAR MÃO',
            'relaxado': '🤚 ABRIR MÃO',
            'neutro': '😐 NEUTRO',
            'sinal_ruim': '⚠️  SINAL RUIM'
        }
        
        print(f"{simbolo[estado]:20s} | "
              f"Atenção: {data.attention:3d} | "
              f"Meditação: {data.meditation:3d} | "
              f"Sinal: {data.signal:3d} | "
              f"Bateria: {data.battery:3d}%")
        
        # Simula comando (sem Arduino)
        if estado != self.estado_atual:
            if estado == 'concentrado':
                print(">>> COMANDO: Fecharia a mão agora")
            elif estado == 'relaxado':
                print(">>> COMANDO: Abriria a mão agora")
            self.estado_atual = estado
    
    def iniciar(self):
        """Inicia o sistema"""
        print("=" * 70)
        print("🧠 TESTE EEG SIMPLIFICADO (SEM ARDUINO)")
        print("=" * 70)
        print(f"Porta: {PORTA_COM_EEG} @ {BAUDRATE} baud")
        print(f"Threshold Concentração: {THRESHOLD_CONCENTRACAO}")
        print(f"Threshold Relaxamento: {THRESHOLD_RELAXAMENTO}")
        print("=" * 70)
        print("\nInstruções:")
        print("  - Concentre-se para simular FECHAR a mão")
        print("  - Relaxe para simular ABRIR a mão")
        print("  - Pressione Ctrl+C para sair")
        print()
        
        # Conecta
        if not self.eeg.connect():
            print("❌ Falha ao conectar. Verifique a porta COM.")
            return
        
        # Registra callback
        self.eeg.add_callback(self.on_eeg_data)
        
        print("✅ Conectado! Lendo dados EEG...\n")
        
        try:
            while True:
                self.eeg.read_once()
                time.sleep(0.05)  # 20 Hz
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Finalizado pelo usuário")
        
        finally:
            self.eeg.disconnect()
            print("✅ Desconectado")


if __name__ == "__main__":
    controle = ControleEEGSimples()
    controle.iniciar()
