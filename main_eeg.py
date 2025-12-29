"""
Controle da Mão Robótica via EEG Brain-link Pro
Concentração = Mão fecha | Relaxamento = Mão abre
"""

import cv2
import time
import numpy as np
from eeg_brainlink import BrainLinkEEG, BrainLinkData
import servo_braco3d as mao

# --- Configurações ---
PORTA_COM_EEG = 'COM5'  # Ajuste conforme sua porta
BAUDRATE = 57600

# Thresholds (ajustáveis via calibração)
THRESHOLD_CONCENTRACAO = 60  # Acima deste valor = concentrado
THRESHOLD_RELAXAMENTO = 60   # Acima deste valor = relaxado
DEBOUNCE_TIME = 1.0  # Segundos para evitar mudanças rápidas

# Estados da mão
ESTADO_ABERTA = 'aberta'
ESTADO_FECHADA = 'fechada'
ESTADO_NEUTRO = 'neutro'

class ControleEEG:
    def __init__(self):
        self.eeg = BrainLinkEEG(port=PORTA_COM_EEG, baudrate=BAUDRATE)
        self.estado_atual = ESTADO_NEUTRO
        self.ultimo_comando = time.time()
        
        # Dados para visualização
        self.attention_value = 0
        self.meditation_value = 0
        self.signal_quality = 200
        self.battery = 0
        
        # Histórico para gráfico
        self.attention_history = []
        self.meditation_history = []
        self.max_history = 100
        
    def on_eeg_data(self, data: BrainLinkData):
        """Callback para processar dados EEG"""
        self.attention_value = data.attention
        self.meditation_value = data.meditation
        self.signal_quality = data.signal
        self.battery = data.battery
        
        # Atualiza histórico
        self.attention_history.append(data.attention)
        self.meditation_history.append(data.meditation)
        
        if len(self.attention_history) > self.max_history:
            self.attention_history.pop(0)
        if len(self.meditation_history) > self.max_history:
            self.meditation_history.pop(0)
        
        # Verifica se pode mudar de estado (debounce)
        tempo_atual = time.time()
        if tempo_atual - self.ultimo_comando < DEBOUNCE_TIME:
            return
        
        # Lógica de controle
        novo_estado = self._determinar_estado(data)
        
        if novo_estado != self.estado_atual:
            self._executar_comando(novo_estado)
            self.estado_atual = novo_estado
            self.ultimo_comando = tempo_atual
    
    def _determinar_estado(self, data: BrainLinkData) -> str:
        """Determina o estado baseado nos valores EEG"""
        # Ignora se sinal ruim
        if data.signal > 100:
            return self.estado_atual
        
        # Concentração alta = Fechar mão
        if data.attention > THRESHOLD_CONCENTRACAO:
            return ESTADO_FECHADA
        
        # Relaxamento alto = Abrir mão
        if data.meditation > THRESHOLD_RELAXAMENTO:
            return ESTADO_ABERTA
        
        # Caso contrário, mantém estado atual
        return self.estado_atual
    
    def _executar_comando(self, estado: str):
        """Executa o comando na mão robótica"""
        pinos = [10, 9, 8, 7, 6]
        
        if estado == ESTADO_FECHADA:
            print("🤜 CONCENTRADO → Fechando mão")
            for pino in pinos:
                mao.abrir_fechar(pino, 0)  # 0 = fechar
        
        elif estado == ESTADO_ABERTA:
            print("🤚 RELAXADO → Abrindo mão")
            for pino in pinos:
                mao.abrir_fechar(pino, 1)  # 1 = abrir
    
    def criar_interface(self) -> np.ndarray:
        """Cria interface visual com dados EEG"""
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        img[:] = (20, 20, 20)  # Fundo escuro
        
        # Título
        cv2.putText(img, "Controle EEG - Mao Robotica", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # Estado atual
        cor_estado = {
            ESTADO_FECHADA: (0, 0, 255),    # Vermelho
            ESTADO_ABERTA: (0, 255, 0),     # Verde
            ESTADO_NEUTRO: (128, 128, 128)  # Cinza
        }
        
        estado_texto = {
            ESTADO_FECHADA: "CONCENTRADO - MAO FECHADA",
            ESTADO_ABERTA: "RELAXADO - MAO ABERTA",
            ESTADO_NEUTRO: "NEUTRO"
        }
        
        cv2.rectangle(img, (20, 70), (780, 130), cor_estado[self.estado_atual], -1)
        cv2.putText(img, estado_texto[self.estado_atual], (40, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Valores atuais
        y_pos = 180
        cv2.putText(img, f"Atencao: {self.attention_value:3d}", (40, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
        
        cv2.putText(img, f"Meditacao: {self.meditation_value:3d}", (40, y_pos + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        
        cv2.putText(img, f"Sinal: {self.signal_quality:3d}", (40, y_pos + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        cv2.putText(img, f"Bateria: {self.battery}%", (40, y_pos + 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 100), 2)
        
        # Barras de progresso
        self._desenhar_barra(img, 300, y_pos - 20, self.attention_value, "Atencao", (255, 200, 0))
        self._desenhar_barra(img, 300, y_pos + 20, self.meditation_value, "Meditacao", (0, 200, 255))
        
        # Linha de threshold
        threshold_x = 300 + int(THRESHOLD_CONCENTRACAO * 4.5)
        cv2.line(img, (threshold_x, y_pos - 30), (threshold_x, y_pos + 50), (255, 0, 0), 2)
        
        # Gráfico histórico
        if len(self.attention_history) > 1:
            self._desenhar_grafico(img, 50, 380, 700, 150)
        
        # Instruções
        cv2.putText(img, "Pressione ESC para sair", (20, 580),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        
        return img
    
    def _desenhar_barra(self, img, x, y, valor, label, cor):
        """Desenha barra de progresso horizontal"""
        largura_max = 450
        largura = int((valor / 100) * largura_max)
        
        # Fundo da barra
        cv2.rectangle(img, (x, y - 10), (x + largura_max, y + 10), (50, 50, 50), -1)
        
        # Barra preenchida
        if largura > 0:
            cv2.rectangle(img, (x, y - 10), (x + largura, y + 10), cor, -1)
        
        # Borda
        cv2.rectangle(img, (x, y - 10), (x + largura_max, y + 10), (100, 100, 100), 2)
    
    def _desenhar_grafico(self, img, x, y, largura, altura):
        """Desenha gráfico de histórico"""
        # Fundo
        cv2.rectangle(img, (x, y), (x + largura, y + altura), (30, 30, 30), -1)
        cv2.rectangle(img, (x, y), (x + largura, y + altura), (100, 100, 100), 2)
        
        # Linha de threshold
        threshold_y = y + altura - int((THRESHOLD_CONCENTRACAO / 100) * altura)
        cv2.line(img, (x, threshold_y), (x + largura, threshold_y), (100, 100, 100), 1)
        
        # Plota atenção
        if len(self.attention_history) > 1:
            pontos = []
            for i, val in enumerate(self.attention_history):
                px = x + int((i / self.max_history) * largura)
                py = y + altura - int((val / 100) * altura)
                pontos.append((px, py))
            
            for i in range(len(pontos) - 1):
                cv2.line(img, pontos[i], pontos[i + 1], (255, 200, 0), 2)
        
        # Plota meditação
        if len(self.meditation_history) > 1:
            pontos = []
            for i, val in enumerate(self.meditation_history):
                px = x + int((i / self.max_history) * largura)
                py = y + altura - int((val / 100) * altura)
                pontos.append((px, py))
            
            for i in range(len(pontos) - 1):
                cv2.line(img, pontos[i], pontos[i + 1], (0, 200, 255), 2)
        
        # Legenda
        cv2.putText(img, "Atencao", (x + 10, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
        cv2.putText(img, "Meditacao", (x + 10, y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
    
    def iniciar(self):
        """Inicia o sistema de controle EEG"""
        print("=" * 60)
        print("🧠 Sistema de Controle EEG - Mão Robótica")
        print("=" * 60)
        print(f"Porta COM: {PORTA_COM_EEG}")
        print(f"Threshold Concentração: {THRESHOLD_CONCENTRACAO}")
        print(f"Threshold Relaxamento: {THRESHOLD_RELAXAMENTO}")
        print("=" * 60)
        
        # Conecta ao EEG
        if not self.eeg.connect():
            print("❌ Falha ao conectar ao Brain-link Pro")
            return
        
        # Registra callback
        self.eeg.add_callback(self.on_eeg_data)
        
        # Abre todos os dedos inicialmente
        print("🤚 Abrindo mão...")
        pinos = [10, 9, 8, 7, 6]
        for pino in pinos:
            mao.abrir_fechar(pino, 1)
        
        # Cria janela
        cv2.namedWindow('Controle EEG', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Controle EEG', 800, 600)
        
        print("✅ Sistema iniciado! Use sua mente para controlar a mão.")
        print("   - Concentre-se para FECHAR a mão")
        print("   - Relaxe para ABRIR a mão")
        print("   - Pressione ESC para sair")
        print()
        
        try:
            while True:
                # Lê dados EEG
                self.eeg.read_once()
                
                # Atualiza interface
                img = self.criar_interface()
                cv2.imshow('Controle EEG', img)
                
                # Verifica tecla
                key = cv2.waitKey(10) & 0xFF
                if key == 27:  # ESC
                    break
                
                # Verifica se janela foi fechada
                if cv2.getWindowProperty('Controle EEG', cv2.WND_PROP_VISIBLE) < 1:
                    break
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n⏹️  Interrompido pelo usuário")
        
        finally:
            # Abre todos os dedos ao finalizar
            print("🤚 Abrindo mão...")
            for pino in pinos:
                mao.abrir_fechar(pino, 1)
            
            self.eeg.disconnect()
            cv2.destroyAllWindows()
            print("✅ Sistema finalizado")


if __name__ == "__main__":
    controle = ControleEEG()
    controle.iniciar()
