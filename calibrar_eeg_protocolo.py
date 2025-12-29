"""
Protocolo de Calibração EEG - Brain-link Pro
Determina os níveis de atenção do usuário em 2 fases:
1. Relaxamento (15s) - olhos fechados, respiração
2. Concentração (15s) - cálculos matemáticos
"""

import serial
import time
import random
import json
import winsound
import os
from eeg_brainlink import BrainLinkParser, BrainLinkData

# Configurações
PORTA_COM_EEG = 'COM6'
BAUDRATE = 57600
DURACAO_FASE = 30  # segundos por fase

class CalibradorEEG:
    def __init__(self):
        self.valores_relaxamento = []
        self.valores_concentracao = []
        self.fase_atual = None
        self.ultimo_valor = 0
        
    def beep(self, frequencia=1000, duracao=500):
        """Emite um beep sonoro"""
        try:
            winsound.Beep(frequencia, duracao)
        except:
            print("\a")  # Fallback para terminal beep
    
    def beep_inicio(self):
        """Beep para indicar início de fase"""
        self.beep(800, 300)
        time.sleep(0.1)
        self.beep(1000, 300)
    
    def beep_fim(self):
        """Beep para indicar fim de fase"""
        self.beep(1200, 200)
        self.beep(1000, 200)
        self.beep(800, 400)
    
    def on_data(self, data: BrainLinkData):
        """Callback para receber dados EEG"""
        self.ultimo_valor = data.attention
        
        if self.fase_atual == 'relaxamento':
            self.valores_relaxamento.append(data.attention)
        elif self.fase_atual == 'concentracao':
            self.valores_concentracao.append(data.attention)
    
    def gerar_calculo(self):
        """Gera um cálculo matemático aleatório"""
        operacoes = ['+', '-', '*']
        op = random.choice(operacoes)
        
        if op == '+':
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            resultado = a + b
        elif op == '-':
            a = random.randint(50, 99)
            b = random.randint(10, a)
            resultado = a - b
        else:  # *
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            resultado = a * b
        
        return f"{a} {op} {b} = ?", resultado
    
    def limpar_tela(self):
        """Limpa a tela do terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def mostrar_barra_progresso(self, tempo_atual, tempo_total, texto=""):
        """Mostra barra de progresso"""
        largura = 40
        progresso = tempo_atual / tempo_total
        preenchido = int(largura * progresso)
        barra = "█" * preenchido + "░" * (largura - preenchido)
        restante = tempo_total - tempo_atual
        print(f"\n{texto}")
        print(f"[{barra}] {restante:.0f}s restantes")
        print(f"\nAtenção atual: {self.ultimo_valor}")
    
    def fase_relaxamento(self, ser, parser):
        """Executa fase de relaxamento"""
        print("\n" + "="*60)
        print("🧘 FASE 1: RELAXAMENTO")
        print("="*60)
        print("\nVocê terá 15 segundos para relaxar.")
        print("Instruções:")
        print("  • Feche os olhos")
        print("  • Respire lenta e profundamente")
        print("  • Não pense em nada específico")
        print("\nPressione ENTER quando estiver pronto...")
        input()
        
        self.beep_inicio()
        self.fase_atual = 'relaxamento'
        self.limpar_tela()
        
        inicio = time.time()
        while time.time() - inicio < DURACAO_FASE:
            # Lê dados EEG
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                parser.parse(data)
            
            self.limpar_tela()
            print("\n" + "="*60)
            print("🧘 RELAXAMENTO - Mantenha os olhos fechados")
            print("="*60)
            print("\n\n")
            print("       Respire... Inspire... Expire...")
            print("\n\n")
            self.mostrar_barra_progresso(
                time.time() - inicio, 
                DURACAO_FASE,
                "Coletando dados de relaxamento..."
            )
            time.sleep(0.5)
        
        self.beep_fim()
        self.fase_atual = None
        print("\n✅ Fase de relaxamento concluída!")
        time.sleep(1)
    
    def fase_concentracao(self, ser, parser):
        """Executa fase de concentração com cálculos"""
        print("\n" + "="*60)
        print("🧮 FASE 2: CONCENTRAÇÃO")
        print("="*60)
        print("\nVocê terá 15 segundos resolvendo cálculos.")
        print("Instruções:")
        print("  • Resolva mentalmente cada cálculo")
        print("  • Pressione ENTER para ver o próximo")
        print("  • Foque ao máximo!")
        print("\nPressione ENTER quando estiver pronto...")
        input()
        
        self.beep_inicio()
        self.fase_atual = 'concentracao'
        
        inicio = time.time()
        calculos_resolvidos = 0
        
        while time.time() - inicio < DURACAO_FASE:
            # Gera novo cálculo
            calculo, resultado = self.gerar_calculo()
            
            self.limpar_tela()
            print("\n" + "="*60)
            print("🧮 CONCENTRAÇÃO - Resolva mentalmente!")
            print("="*60)
            print("\n\n")
            print(f"        {calculo}")
            print("\n\n")
            self.mostrar_barra_progresso(
                time.time() - inicio, 
                DURACAO_FASE,
                "Pressione ENTER para próximo cálculo..."
            )
            
            # Aguarda ENTER ou timeout
            import msvcrt
            tempo_calculo = time.time()
            while time.time() - tempo_calculo < 3:  # Max 3s por cálculo
                # Lê dados EEG
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    parser.parse(data)
                
                # Verifica se pressionou tecla
                if msvcrt.kbhit():
                    msvcrt.getch()
                    calculos_resolvidos += 1
                    print(f"\n   Resposta: {resultado}")
                    time.sleep(0.3)
                    break
                
                time.sleep(0.05)
                
                # Verifica tempo total
                if time.time() - inicio >= DURACAO_FASE:
                    break
        
        self.beep_fim()
        self.fase_atual = None
        print(f"\n✅ Fase de concentração concluída!")
        print(f"   Cálculos resolvidos: {calculos_resolvidos}")
        time.sleep(1)
    
    def calcular_resultados(self):
        """Calcula médias e define threshold"""
        if not self.valores_relaxamento or not self.valores_concentracao:
            print("❌ Dados insuficientes para calibração")
            return None
        
        media_relaxamento = sum(self.valores_relaxamento) / len(self.valores_relaxamento)
        media_concentracao = sum(self.valores_concentracao) / len(self.valores_concentracao)
        
        # Threshold = média entre os dois estados
        threshold = (media_relaxamento + media_concentracao) / 2
        
        return {
            'media_relaxamento': round(media_relaxamento, 1),
            'media_concentracao': round(media_concentracao, 1),
            'threshold': round(threshold, 1),
            'amostras_relaxamento': len(self.valores_relaxamento),
            'amostras_concentracao': len(self.valores_concentracao),
            'data_calibracao': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def salvar_calibracao(self, resultados):
        """Salva resultados em arquivo JSON"""
        arquivo = 'calibracao_eeg.json'
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Calibração salva em: {arquivo}")
    
    def executar(self):
        """Executa o protocolo completo de calibração"""
        self.limpar_tela()
        print("="*60)
        print("🧠 PROTOCOLO DE CALIBRAÇÃO EEG")
        print("="*60)
        print("\nEste protocolo irá calibrar o sistema para seu perfil.")
        print("\nFases:")
        print("  1️⃣  Relaxamento (15s) - Olhos fechados, respiração")
        print("  2️⃣  Concentração (15s) - Cálculos matemáticos")
        print("\n⚠️  Certifique-se de que:")
        print("  • Brain-link Pro está conectado e posicionado")
        print("  • Ambiente silencioso")
        print("  • Você não será interrompido")
        
        input("\n▶️  Pressione ENTER para conectar ao EEG...")
        
        # Conectar ao EEG
        try:
            print(f"\n🔌 Conectando a {PORTA_COM_EEG}...")
            parser = BrainLinkParser(self.on_data)
            ser = serial.Serial(PORTA_COM_EEG, BAUDRATE, timeout=1)
            print("✅ Conectado!")
            
            # Aguarda estabilização
            print("⏳ Aguardando estabilização do sinal (5s)...")
            time.sleep(5)
            
            # Executa fases
            self.fase_relaxamento(ser, parser)
            self.fase_concentracao(ser, parser)
            
            # Fecha conexão
            ser.close()
            
            # Calcula resultados
            self.limpar_tela()
            print("\n" + "="*60)
            print("📊 RESULTADOS DA CALIBRAÇÃO")
            print("="*60)
            
            resultados = self.calcular_resultados()
            
            if resultados:
                print(f"\n🧘 Média durante RELAXAMENTO: {resultados['media_relaxamento']}")
                print(f"   ({resultados['amostras_relaxamento']} amostras coletadas)")
                
                print(f"\n🧮 Média durante CONCENTRAÇÃO: {resultados['media_concentracao']}")
                print(f"   ({resultados['amostras_concentracao']} amostras coletadas)")
                
                print(f"\n🎯 THRESHOLD RECOMENDADO: {resultados['threshold']}")
                print(f"   (Mão fecha quando atenção >= {resultados['threshold']})")
                
                # Salva calibração
                self.salvar_calibracao(resultados)
                
                print("\n" + "="*60)
                print("✅ Calibração concluída com sucesso!")
                print("="*60)
                print("\nPróximos passos:")
                print("  • Execute: python main_eeg.py")
                print("  • O threshold será carregado automaticamente")
            
        except serial.SerialException as e:
            print(f"\n❌ Erro de conexão: {e}")
        except KeyboardInterrupt:
            print("\n\n⏹️  Calibração cancelada pelo usuário")


if __name__ == "__main__":
    calibrador = CalibradorEEG()
    calibrador.executar()
