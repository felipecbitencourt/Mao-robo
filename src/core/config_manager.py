import json
import os
import sys

class ConfigManager:
    """
    Gerenciador de configurações persistentes para o Mao-robo.
    Salva as preferências e calibrações no arquivo config.json na raiz do projeto
    ou na raiz do repositório executável nativo.
    """
    def __init__(self, filename="config.json"):
        if getattr(sys, 'frozen', False):
            # Se empacotado pelo PyInstaller, gravar ao lado do executável final
            base_dir = os.path.dirname(sys.executable)
        else:
            # Diretório raiz (Mao-robo) local no código
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.filepath = os.path.join(base_dir, filename)
        
        # Configuração padrão caso o arquivo não exista
        self.config = {
            "arduino_port": "COM5",
            "theme_dark_mode": True,
            "glove_calibration": {}
        }
        self.load()

    def load(self):
        """Carrega as configurações do arquivo JSON (se existir)"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Mescla a config carregada com o dicionário padrão (evita que chaves novas quebrem)
                    self.config.update(data)
                print(f"[ConfigManager] Configurações recarregadas com sucesso de {self.filepath}")
            except Exception as e:
                print(f"[ConfigManager] Erro ao carregar '{self.filepath}': {e}")
        else:
            print(f"[ConfigManager] Arquivo config.json não encontrado. Usando definições padrão.")

    def save(self):
        """Salva as configurações atuais no arquivo JSON"""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"[ConfigManager] Status salvo em '{self.filepath}'")
        except Exception as e:
            print(f"[ConfigManager] Erro fatal ao tentar salvar o arquivo: {e}")

    def get(self, key, default=None):
        """Recupera o valor de uma chave específica"""
        return self.config.get(key, default)

    def set(self, key, value):
        """Atualiza e salva instantaneamente o valor de uma chave específica"""
        self.config[key] = value
        self.save()
