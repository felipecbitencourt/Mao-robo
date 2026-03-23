# core/state_manager.py
import json
import uuid
import datetime
import os


class StateManager:
    """
    Gerencia todos os estados da aplicação:
        - Informações da sessão
        - Dados de calibração
        - Dados processados/exportáveis
        - Estados entre telas (GUI)
        - Salvamento e carregamento via JSON

    Usado pela ClinicalGloveApp.
    """

    def __init__(self, base_data_dir="data"):
        self.base_dir = base_data_dir

        # Diretórios estruturados
        self.sessions_dir = os.path.join(self.base_dir, "sessions")
        self.exports_dir = os.path.join(self.base_dir, "exports")

        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)

        # Estados internos
        self.current_screen = "menu"
        self.session_data = None
        self.calibration_results = None
        self.sensor_disabled_mask = None

        # Ao iniciar, cria nova sessão
        self.new_session()

    # ================================================================
    # SESSÃO
    # ================================================================
    def new_session(self, patient_name="Paciente", mode="cycles"):
        """Cria estrutura inicial de uma nova sessão."""
        session_id = str(uuid.uuid4())

        self.session_data = {
            "session_id": session_id,
            "patient_name": patient_name,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "sensor_disabled_mask": [],      # preenchido após calibração
            "calibration_results": None,     # thresholds etc.
            "notes": "",
        }

    def set_screen(self, screen_name):
        """Atualiza tela atual da aplicação."""
        self.current_screen = screen_name

    def set_disabled_mask(self, mask):
        """Salva quais sensores foram desativados antes da calibração."""
        self.sensor_disabled_mask = mask
        self.session_data["sensor_disabled_mask"] = mask

    # ================================================================
    # SALVAR RESULTADOS DA CALIBRAÇÃO
    # ================================================================
    def store_calibration(self, calib_data: dict):
        """Guarda dados retornados por CalibrationManager.get_export_data()."""
        self.calibration_results = calib_data
        self.session_data["calibration_results"] = calib_data

    # ================================================================
    # EXPORTAÇÃO DE CALIBRAÇÃO E SESSÃO
    # ================================================================
    def save_session(self):
        """
        Salva arquivo JSON completo dentro de data/sessions/<id>.json
        """

        if not self.session_data:
            raise RuntimeError("Nenhuma sessão ativa para salvar.")

        file_path = os.path.join(self.sessions_dir, f"{self.session_data['session_id']}.json")

        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(self.session_data, fp, indent=4, ensure_ascii=False)

        return file_path

    def load_session(self, session_id):
        """
        Carrega um arquivo JSON de sessão.
        """
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Sessão {session_id} não encontrada.")

        with open(file_path, "r", encoding="utf-8") as fp:
            self.session_data = json.load(fp)

        self.calibration_results = self.session_data.get("calibration_results")
        self.sensor_disabled_mask = self.session_data.get("sensor_disabled_mask")

        return self.session_data

    # ================================================================
    # EXPORTA RESULTADOS PARA USO EXTERNO (pesquisa, CSV etc.)
    # ================================================================
    def export_calibration(self, filename="calibration_export.json"):
        if not self.calibration_results:
            raise RuntimeError("Nenhum dado de calibração para exportar.")

        fp = os.path.join(self.exports_dir, filename)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(self.calibration_results, f, indent=4, ensure_ascii=False)
        return fp

    # ================================================================
    # UTILITÁRIOS
    # ================================================================
    def list_sessions(self):
        """
        Retorna lista de IDs de sessões salvas.
        """
        files = os.listdir(self.sessions_dir)
        return [f.replace(".json", "") for f in files if f.endswith(".json")]
