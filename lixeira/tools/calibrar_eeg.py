"""
Script de Calibração - Brain-link Pro
Ajusta thresholds personalizados de concentração e relaxamento
"""

import time
import json
from eeg_brainlink import BrainLinkEEG, BrainLinkData
from collections import deque

class CalibradorEEG:
    def __init__(self, porta='COM5', baudrate=57600):
        self.eeg = BrainLinkEEG(port=porta, baudrate=baudrate)
        self.amostras_baseline = []
        self.amostras_concentracao = []
        self.amostras_relaxamento = []
        
    def coletar_amostras(self, duracao: int, nome_fase: str) -> list:
        """Coleta amostras por um período de tempo"""
        amostras = []
        inicio = time.time()
        
        print(f"\n{'='*60}")
        print(f"📊 Fase: {nome_fase}")
        print(f"⏱️  Duração: {duracao} segundos")
        print(f"{'='*60}")
        
        # Callback para coletar dados
        def coletar(data: BrainLinkData):
            if data.signal < 100:  # Apenas se sinal bom
                amostras.append({
                    'attention': data.attention,
                    'meditation': data.meditation,
                    'timestamp': time.time()
                })
        
        self.eeg.add_callback(coletar)
        
        # Contagem regressiva
        for i in range(3, 0, -1):
            print(f"Começando em {i}...")
            time.sleep(1)
        
        print("🟢 INICIADO! Mantenha o estado...")
        
        # Coleta dados
        tempo_decorrido = 0
        while tempo_decorrido < duracao:
            self.eeg.read_once()
            tempo_decorrido = time.time() - inicio
            
            # Mostra progresso
            if int(tempo_decorrido) % 5 == 0 and tempo_decorrido > 0:
                restante = duracao - int(tempo_decorrido)
                if restante > 0 and restante % 5 == 0:
                    print(f"⏳ {restante} segundos restantes...")
            
            time.sleep(0.01)
        
        print(f"✅ Fase concluída! Coletadas {len(amostras)} amostras")
        
        # Remove callback
        self.eeg.callbacks.clear()
        
        return amostras
    
    def calcular_thresholds(self):
        """Calcula thresholds baseados nas amostras coletadas"""
        print(f"\n{'='*60}")
        print("📈 Analisando dados coletados...")
        print(f"{'='*60}")
        
        # Calcula médias
        if not self.amostras_concentracao or not self.amostras_relaxamento:
            print("❌ Dados insuficientes para calibração")
            return None
        
        # Atenção durante concentração
        attention_concentrado = [s['attention'] for s in self.amostras_concentracao]
        media_attention = sum(attention_concentrado) / len(attention_concentrado)
        max_attention = max(attention_concentrado)
        
        # Meditação durante relaxamento
        meditation_relaxado = [s['meditation'] for s in self.amostras_relaxamento]
        media_meditation = sum(meditation_relaxado) / len(meditation_relaxado)
        max_meditation = max(meditation_relaxado)
        
        # Baseline
        if self.amostras_baseline:
            baseline_attention = [s['attention'] for s in self.amostras_baseline]
            baseline_meditation = [s['meditation'] for s in self.amostras_baseline]
            media_baseline_att = sum(baseline_attention) / len(baseline_attention)
            media_baseline_med = sum(baseline_meditation) / len(baseline_meditation)
        else:
            media_baseline_att = 30
            media_baseline_med = 30
        
        # Calcula thresholds (70% do valor máximo, mas acima do baseline)
        threshold_concentracao = max(int(max_attention * 0.7), int(media_baseline_att + 15))
        threshold_relaxamento = max(int(max_meditation * 0.7), int(media_baseline_med + 15))
        
        # Garante valores razoáveis
        threshold_concentracao = max(40, min(80, threshold_concentracao))
        threshold_relaxamento = max(40, min(80, threshold_relaxamento))
        
        print(f"\n📊 Resultados da Calibração:")
        print(f"   Baseline Atenção: {media_baseline_att:.1f}")
        print(f"   Baseline Meditação: {media_baseline_med:.1f}")
        print(f"   Atenção Concentrado: {media_attention:.1f} (max: {max_attention})")
        print(f"   Meditação Relaxado: {media_meditation:.1f} (max: {max_meditation})")
        print(f"\n🎯 Thresholds Recomendados:")
        print(f"   Concentração: {threshold_concentracao}")
        print(f"   Relaxamento: {threshold_relaxamento}")
        
        return {
            'threshold_concentracao': threshold_concentracao,
            'threshold_relaxamento': threshold_relaxamento,
            'porta_com': self.eeg.port,
            'baudrate': self.eeg.baudrate,
            'data_calibracao': time.strftime('%Y-%m-%d %H:%M:%S'),
            'estatisticas': {
                'baseline_attention': media_baseline_att,
                'baseline_meditation': media_baseline_med,
                'concentracao_attention_media': media_attention,
                'concentracao_attention_max': max_attention,
                'relaxamento_meditation_media': media_meditation,
                'relaxamento_meditation_max': max_meditation
            }
        }
    
    def salvar_configuracao(self, config: dict, arquivo='eeg_config.json'):
        """Salva configuração em arquivo JSON"""
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"\n💾 Configuração salva em: {arquivo}")
    
    def executar_calibracao(self):
        """Executa processo completo de calibração"""
        print("=" * 60)
        print("🧠 CALIBRAÇÃO DO BRAIN-LINK PRO")
        print("=" * 60)
        print("\nEste processo irá calibrar os thresholds personalizados")
        print("para seu padrão cerebral único.")
        print("\nVocê passará por 3 fases:")
        print("  1. Baseline (estado neutro)")
        print("  2. Concentração (foco mental)")
        print("  3. Relaxamento (meditação)")
        print("\nCertifique-se de que o Brain-link Pro está:")
        print("  ✓ Bem posicionado na cabeça")
        print("  ✓ Com sensores em contato com a pele")
        print("  ✓ Conectado via Bluetooth")
        
        input("\n▶️  Pressione ENTER para começar...")
        
        # Conecta ao EEG
        if not self.eeg.connect():
            print("❌ Falha ao conectar. Verifique a porta COM e o pareamento.")
            return
        
        try:
            # Fase 1: Baseline
            print("\n" + "=" * 60)
            print("FASE 1: BASELINE")
            print("=" * 60)
            print("Instruções:")
            print("  - Fique em estado neutro")
            print("  - Não pense em nada específico")
            print("  - Respire normalmente")
            
            input("\n▶️  Pressione ENTER quando estiver pronto...")
            self.amostras_baseline = self.coletar_amostras(30, "Baseline")
            
            # Pausa
            print("\n⏸️  Pausa de 10 segundos...")
            time.sleep(10)
            
            # Fase 2: Concentração
            print("\n" + "=" * 60)
            print("FASE 2: CONCENTRAÇÃO")
            print("=" * 60)
            print("Instruções:")
            print("  - Concentre-se intensamente")
            print("  - Conte de 100 para 0 de 3 em 3")
            print("  - Ou resolva problemas matemáticos mentalmente")
            print("  - Mantenha o foco máximo!")
            
            input("\n▶️  Pressione ENTER quando estiver pronto...")
            self.amostras_concentracao = self.coletar_amostras(30, "Concentração")
            
            # Pausa
            print("\n⏸️  Pausa de 10 segundos...")
            time.sleep(10)
            
            # Fase 3: Relaxamento
            print("\n" + "=" * 60)
            print("FASE 3: RELAXAMENTO")
            print("=" * 60)
            print("Instruções:")
            print("  - Relaxe completamente")
            print("  - Respire profunda e lentamente")
            print("  - Esvazie a mente")
            print("  - Medite ou apenas relaxe")
            
            input("\n▶️  Pressione ENTER quando estiver pronto...")
            self.amostras_relaxamento = self.coletar_amostras(30, "Relaxamento")
            
            # Calcula e salva
            config = self.calcular_thresholds()
            
            if config:
                self.salvar_configuracao(config)
                
                print("\n" + "=" * 60)
                print("✅ CALIBRAÇÃO CONCLUÍDA COM SUCESSO!")
                print("=" * 60)
                print("\nPróximos passos:")
                print("  1. Execute: python main_eeg.py")
                print("  2. Use sua mente para controlar a mão robótica!")
                print("\nOs thresholds foram salvos e serão carregados automaticamente.")
            
        except KeyboardInterrupt:
            print("\n⏹️  Calibração cancelada pelo usuário")
        
        finally:
            self.eeg.disconnect()


if __name__ == "__main__":
    calibrador = CalibradorEEG(porta='COM5', baudrate=57600)
    calibrador.executar_calibracao()
