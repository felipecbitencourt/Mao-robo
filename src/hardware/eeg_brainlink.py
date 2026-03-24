"""
Módulo de interface com Brain-link Pro EEG
Decodifica dados do protocolo ThinkGear sem dependência do SDK oficial
Compatível com Python 3.13+
"""

import serial
import serial.tools.list_ports
import time
import traceback
from collections import deque
from typing import Callable, Optional

class BrainLinkData:
    """Dados EEG processados do Brain-link Pro"""
    def __init__(self):
        self.signal = 200  # Qualidade do sinal (0=melhor, 200=sem contato)
        self.attention = 0  # Concentração (0-100)
        self.meditation = 0  # Relaxamento (0-100)
        self.delta = 0
        self.theta = 0
        self.low_alpha = 0
        self.high_alpha = 0
        self.low_beta = 0
        self.high_beta = 0
        self.low_gamma = 0
        self.high_gamma = 0
        self.raw = 0
        self.battery = 0
        self.heart_rate = 0

class BrainLinkParser:
    """Parser para protocolo ThinkGear do Brain-link Pro"""
    
    # Códigos do protocolo ThinkGear
    SYNC = 0xAA
    EXCODE = 0x55
    
    # Códigos de dados
    CODE_SIGNAL_QUALITY = 0x02
    CODE_ATTENTION = 0x04
    CODE_MEDITATION = 0x05
    CODE_RAW_VALUE = 0x80
    CODE_ASIC_EEG_POWER = 0x83
    CODE_BATTERY = 0x01
    CODE_HEART_RATE = 0x03
    
    def __init__(self, eeg_callback: Optional[Callable] = None):
        self.eeg_callback = eeg_callback
        self.data = BrainLinkData()
        self.buffer = bytearray()
        
    def parse(self, byte_data: bytes):
        """Processa bytes recebidos e extrai dados EEG"""
        self.buffer.extend(byte_data)
        
        while len(self.buffer) >= 4:
            # Procura por sincronização (0xAA 0xAA)
            if self.buffer[0] != self.SYNC:
                self.buffer.pop(0)
                continue
                
            if len(self.buffer) < 2 or self.buffer[1] != self.SYNC:
                self.buffer.pop(0)
                continue
            
            # Encontrou sincronização
            if len(self.buffer) < 4:
                break
                
            # Lê o tamanho do payload
            payload_length = self.buffer[2]
            
            # Verifica se temos o pacote completo
            packet_length = 4 + payload_length  # SYNC + SYNC + LENGTH + PAYLOAD + CHECKSUM
            if len(self.buffer) < packet_length:
                break
            
            # Extrai o pacote
            packet = self.buffer[:packet_length]
            
            # Verifica checksum
            payload = packet[3:-1]
            checksum = packet[-1]
            
            calculated_checksum = self._calculate_checksum(payload)
            
            if checksum == calculated_checksum:
                # Pacote válido, processa payload
                self._parse_payload(payload)
                
                # Chama callback se disponível
                if self.eeg_callback:
                    self.eeg_callback(self.data)
            
            # Remove o pacote processado do buffer
            self.buffer = self.buffer[packet_length:]
    
    def _calculate_checksum(self, payload: bytes) -> int:
        """Calcula checksum do payload"""
        checksum = sum(payload) & 0xFF
        return (~checksum) & 0xFF
    
    def _parse_payload(self, payload: bytes):
        """Decodifica o payload e atualiza os dados"""
        i = 0
        while i < len(payload):
            # Pula EXCODEs
            while i < len(payload) and payload[i] == self.EXCODE:
                i += 1
            
            if i >= len(payload):
                break
            
            code = payload[i]
            i += 1
            
            # Determina o tamanho do valor
            if code >= 0x80:
                # Código com tamanho variável
                if i >= len(payload):
                    break
                value_length = payload[i]
                i += 1
                
                if i + value_length > len(payload):
                    break
                
                value_bytes = payload[i:i + value_length]
                i += value_length
                
                self._process_code(code, value_bytes)
            else:
                # Código de 1 byte
                if i >= len(payload):
                    break
                value = payload[i]
                i += 1
                
                self._process_code(code, bytes([value]))
    
    def _process_code(self, code: int, value_bytes: bytes):
        """Processa um código específico"""
        if code == self.CODE_SIGNAL_QUALITY:
            self.data.signal = value_bytes[0]
        
        elif code == self.CODE_ATTENTION:
            self.data.attention = value_bytes[0]
        
        elif code == self.CODE_MEDITATION:
            self.data.meditation = value_bytes[0]
        
        elif code == self.CODE_BATTERY:
            self.data.battery = value_bytes[0]
        
        elif code == self.CODE_HEART_RATE:
            self.data.heart_rate = value_bytes[0]
        
        elif code == self.CODE_RAW_VALUE:
            if len(value_bytes) >= 2:
                self.data.raw = int.from_bytes(value_bytes[:2], byteorder='big', signed=True)
        
        elif code == self.CODE_ASIC_EEG_POWER:
            # Decodifica as bandas de frequência (8 valores de 3 bytes cada)
            if len(value_bytes) >= 24:
                self.data.delta = self._bytes_to_int(value_bytes[0:3])
                self.data.theta = self._bytes_to_int(value_bytes[3:6])
                self.data.low_alpha = self._bytes_to_int(value_bytes[6:9])
                self.data.high_alpha = self._bytes_to_int(value_bytes[9:12])
                self.data.low_beta = self._bytes_to_int(value_bytes[12:15])
                self.data.high_beta = self._bytes_to_int(value_bytes[15:18])
                self.data.low_gamma = self._bytes_to_int(value_bytes[18:21])
                self.data.high_gamma = self._bytes_to_int(value_bytes[21:24])
    
    def _bytes_to_int(self, bytes_data: bytes) -> int:
        """Converte 3 bytes para inteiro (big-endian)"""
        return int.from_bytes(bytes_data, byteorder='big')


class BrainLinkEEG:
    """Interface de alto nível para Brain-link Pro"""
    
    def __init__(self, port: str = 'COM5', baudrate: int = 57600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.parser = None
        self.running = False
        self.callbacks = []
        
        # Histórico para média móvel
        self.attention_history = deque(maxlen=5)
        self.meditation_history = deque(maxlen=5)
        
    def connect(self) -> bool:
        """Conecta ao Brain-link Pro"""
        print("\n" + "="*60)
        print("🔍 DEBUG: Iniciando processo de conexão...")
        print("="*60)
        
        # Lista todas as portas disponíveis
        print("\n📋 Portas COM disponíveis:")
        portas = list(serial.tools.list_ports.comports())
        if not portas:
            print("   ⚠️  Nenhuma porta COM encontrada!")
        else:
            for porta in portas:
                print(f"   • {porta.device}: {porta.description}")
                print(f"     - HWID: {porta.hwid}")
                print(f"     - VID:PID: {porta.vid}:{porta.pid}")
                print(f"     - Fabricante: {porta.manufacturer}")
        
        print(f"\n🎯 Tentando conectar em: {self.port}")
        print(f"   - Baudrate: {self.baudrate}")
        print(f"   - Timeout: 1s")
        
        # Verifica se a porta solicitada existe
        portas_disponiveis = [p.device for p in portas]
        if self.port not in portas_disponiveis:
            print(f"\n⚠️  AVISO: {self.port} não está na lista de portas disponíveis!")
            print(f"   Portas disponíveis: {portas_disponiveis}")
        
        try:
            print("\n🔌 Abrindo conexão serial...")
            # Usando mesma sintaxe do testar_eeg.py que funciona
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"   ✓ Porta aberta: {self.serial.is_open}")
            print(f"   ✓ Nome: {self.serial.name}")
            print(f"   ✓ Baudrate: {self.serial.baudrate}")
            
            self.parser = BrainLinkParser(self._on_eeg_data)
            print(f"\n✅ Conectado ao Brain-link Pro na porta {self.port}")
            print("="*60 + "\n")
            return True
            
        except serial.SerialException as e:
            print(f"\n❌ SerialException: {e}")
            print(f"   Tipo do erro: {type(e).__name__}")
            print(f"\n📝 Stack trace:")
            traceback.print_exc()
            print("\n💡 Possíveis soluções:")
            print("   1. Feche outros programas que usam a porta (Termite, Arduino IDE, etc.)")
            print("   2. Desconecte e reconecte o dispositivo USB")
            print("   3. Verifique se o driver Bluetooth está instalado")
            print("   4. Tente reiniciar o computador")
            print("   5. Verifique no Gerenciador de Dispositivos")
            print("="*60 + "\n")
            return False
            
        except Exception as e:
            print(f"\n❌ Erro inesperado: {e}")
            print(f"   Tipo: {type(e).__name__}")
            traceback.print_exc()
            print("="*60 + "\n")
            return False
    
    def disconnect(self):
        """Desconecta do Brain-link Pro"""
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("✅ Desconectado do Brain-link Pro")
    
    def add_callback(self, callback: Callable):
        """Adiciona callback para receber dados processados"""
        self.callbacks.append(callback)
    
    def _on_eeg_data(self, data: BrainLinkData):
        """Callback interno para processar dados EEG"""
        # Adiciona ao histórico para suavização
        self.attention_history.append(data.attention)
        self.meditation_history.append(data.meditation)
        
        # Notifica callbacks externos
        for callback in self.callbacks:
            callback(data)
    
    def get_attention(self) -> int:
        """Retorna nível de atenção/concentração (média móvel)"""
        if not self.attention_history:
            return 0
        return int(sum(self.attention_history) / len(self.attention_history))
    
    def get_meditation(self) -> int:
        """Retorna nível de meditação/relaxamento (média móvel)"""
        if not self.meditation_history:
            return 0
        return int(sum(self.meditation_history) / len(self.meditation_history))
    
    def read_loop(self):
        """Loop de leitura contínua (bloqueante)"""
        if not self.serial or not self.serial.is_open:
            print("❌ Não conectado. Chame connect() primeiro.")
            return
        
        self.running = True
        print("📡 Iniciando leitura de dados EEG...")
        
        try:
            while self.running:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    self.parser.parse(data)
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n⏹️  Leitura interrompida pelo usuário")
        finally:
            self.disconnect()
    
    def read_once(self):
        """Lê dados uma vez (não-bloqueante)"""
        if not self.serial or not self.serial.is_open:
            return
        
        if self.serial.in_waiting > 0:
            data = self.serial.read(self.serial.in_waiting)
            self.parser.parse(data)


# Teste standalone
if __name__ == "__main__":
    def on_data(data: BrainLinkData):
        print(f"🧠 Atenção: {data.attention:3d} | Meditação: {data.meditation:3d} | "
              f"Sinal: {data.signal:3d} | Bateria: {data.battery}%")
    
    # Teste com COM5 (ajuste conforme necessário)
    eeg = BrainLinkEEG(port='COM5', baudrate=57600)
    
    if eeg.connect():
        eeg.add_callback(on_data)
        eeg.read_loop()
