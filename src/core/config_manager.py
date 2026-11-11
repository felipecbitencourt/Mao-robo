import json
import os
import sys
import tempfile


class ConfigManager:
    """
    Configurações persistentes do Mao-robo.

    - ``config.json`` (versionado no git) traz os valores padrão do projeto.
    - ``config.local.json`` (ignorado pelo git) guarda o estado desta máquina:
      portas, câmeras, calibrações e preferências. É o único arquivo gravado.

    Na primeira execução, se ``config.local.json`` não existir, ele é criado com
    o conteúdo atual de ``config.json``, para não perder calibrações antigas.
    A gravação é atômica (arquivo temporário + os.replace): um travamento no
    meio da escrita não corrompe a configuração.
    """

    LOCAL_FILENAME = "config.local.json"

    def __init__(self, filename="config.json", base_dir=None):
        if base_dir is not None:
            defaults_dir = base_dir
        elif getattr(sys, 'frozen', False):
            # Empacotado pelo PyInstaller: estado gravado ao lado do executável,
            # padrões lidos do config.json embutido no pacote
            base_dir = os.path.dirname(sys.executable)
            # (um config.json antigo ao lado do .exe tem prioridade, para migrar)
            if os.path.exists(os.path.join(base_dir, filename)):
                defaults_dir = base_dir
            else:
                defaults_dir = getattr(sys, '_MEIPASS', base_dir)
        else:
            # Raiz do repositório (src/core/config_manager.py -> ../../)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            defaults_dir = base_dir

        self.defaults_path = os.path.join(defaults_dir, filename)
        self.filepath = os.path.join(base_dir, self.LOCAL_FILENAME)

        # Configuração padrão caso nenhum arquivo exista
        self.config = {
            "arduino_port": "COM5",
            "theme_dark_mode": True,
            "glove_calibration": {}
        }
        self.load()

    @staticmethod
    def _read_json(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("o arquivo não contém um objeto JSON")
        return data

    def load(self):
        """Carrega padrões (config.json) e, por cima, o estado local."""
        if os.path.exists(self.defaults_path):
            try:
                self.config.update(self._read_json(self.defaults_path))
            except Exception as e:
                print(f"[ConfigManager] Erro ao ler padrões '{self.defaults_path}': {e}")

        if os.path.exists(self.filepath):
            try:
                self.config.update(self._read_json(self.filepath))
                print(f"[ConfigManager] Configurações carregadas de {self.filepath}")
            except Exception as e:
                # Não sobrescreve o arquivo com problema: guarda uma cópia para análise
                backup = self.filepath + ".corrompido"
                try:
                    os.replace(self.filepath, backup)
                except OSError:
                    pass
                print(f"[ConfigManager] Erro ao ler '{self.filepath}' ({e}). Cópia salva em '{backup}'.")
        else:
            # Primeira execução com o arquivo local: migra o estado atual
            self.save()

    def save(self):
        """Grava o estado em config.local.json de forma atômica."""
        directory = os.path.dirname(self.filepath) or "."
        try:
            fd, tmp = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.filepath)
            except BaseException:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise
        except Exception as e:
            print(f"[ConfigManager] Erro ao salvar '{self.filepath}': {e}")

    def get(self, key, default=None):
        """Recupera o valor de uma chave específica"""
        return self.config.get(key, default)

    def set(self, key, value):
        """Atualiza e salva instantaneamente o valor de uma chave específica"""
        self.config[key] = value
        self.save()
