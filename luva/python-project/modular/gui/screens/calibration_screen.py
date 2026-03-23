# gui/screens/calibration_screen.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
import re

from core.calibration_mode import CalibrationMode
from gui.widgets.sensor_list import SensorList
from gui.widgets.led_indicator import LEDIndicator


class CalibrationScreen(tk.Frame):
    """Tela de calibração baseada no novo CalibrationMode."""

    def __init__(self, master, app):
        super().__init__(master, bg="#f0f4f8")
        self.app = app
        self.pack(expand=True, fill="both")

        # Instância do modo de calibração
        self.calib = CalibrationMode(sensor_names=self.app.calibration_data["sensor_min"])

        # Registrar callbacks GUI
        self.calib.on_cycle_start = self.on_cycle_start
        self.calib.on_cycle_progress = self.on_cycle_progress
        self.calib.on_cycle_end = self.on_cycle_end
        self.calib.on_continuous_update = self.on_continuous_update
        self.calib.on_finish = self.on_finish

        self.build_ui()

        # Cortina de dados da luva
        self.root = self.app.root

    # ============================================================
    # INTERFACE
    # ============================================================
    def build_ui(self):
        title = tk.Label(
            self, text="Calibração da Luva",
            font=("Helvetica", 20, "bold"),
            bg="#f0f4f8", fg="#1a202c"
        )
        title.pack(pady=20)

        # Indicador da luva
        self.led = LEDIndicator(self, label="Status da Luva")
        self.led.pack(pady=5)

        # Container central
        main_frame = tk.Frame(self, bg="white", relief="groove", borderwidth=2)
        main_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # --- Seleção de modo ---
        mode_frame = tk.Frame(main_frame, bg="white")
        mode_frame.pack(pady=10)

        tk.Label(
            mode_frame, text="Modo de Calibração:",
            font=("Helvetica", 12, "bold"), bg="white"
        ).grid(row=0, column=0, padx=5)

        self.mode_var = tk.StringVar(value="cycles")
        ttk.Radiobutton(mode_frame, text="Ciclos", value="cycles",
                        variable=self.mode_var).grid(row=0, column=1)
        ttk.Radiobutton(mode_frame, text="Contínuo", value="continuous",
                        variable=self.mode_var).grid(row=0, column=2)

        # --- Parâmetros ---
        param_frame = tk.Frame(main_frame, bg="white")
        param_frame.pack(pady=10)

        tk.Label(param_frame, text="Nº de ciclos:", bg="white").grid(row=0, column=0)
        tk.Label(param_frame, text="Duração (s):", bg="white").grid(row=1, column=0)

        self.entry_cycles = tk.Entry(param_frame, width=5)
        self.entry_cycles.insert(0, "10")
        self.entry_cycles.grid(row=0, column=1, padx=5)

        self.entry_duration = tk.Entry(param_frame, width=5)
        self.entry_duration.insert(0, "4")
        self.entry_duration.grid(row=1, column=1, padx=5)

        # --- Lista de sensores ---
        tk.Label(
            main_frame, text="Sensores Ativos",
            font=("Helvetica", 12, "bold"), bg="white"
        ).pack(pady=5)

        self.sensor_list = SensorList(
            main_frame,
            sensor_values=[0.0] * len(self.app.calibration_data["sensor_min"]),
            allow_selection=True
        )
        self.sensor_list.pack(fill="both", expand=True, padx=10, pady=10)

        # Progresso
        self.progress = ttk.Progressbar(self, length=300, mode="determinate")
        self.progress.pack(pady=10)

        # Botão: salvar sessão (abre diálogo para nome/idade)
        save_btn = tk.Button(
            self, text="Salvar Sessão",
            font=("Helvetica", 11, "bold"),
            bg="#06b6d4", fg="white",
            padx=10, pady=6,
            command=self.show_save_dialog
        )
        save_btn.pack(pady=(0, 12))
        # Botões
        btn_frame = tk.Frame(self, bg="#f0f4f8")
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Iniciar Calibração",
            font=("Helvetica", 13, "bold"),
            bg="#3B82F6", fg="white",
            padx=25, pady=8,
            command=self.start_calibration
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame, text="Ver Resultados",
            font=("Helvetica", 13, "bold"),
            bg="#10B981", fg="white",
            padx=25, pady=8,
            command=self.go_to_results
        ).pack(side="left", padx=10)

    # ============================================================
    # INTEGRAÇÃO COM CalibrationMode
    # ============================================================
    def start_calibration(self):
        """Inicia o modo de calibração real."""

        if not self.app.glove_connected:
            messagebox.showerror("Erro", "A luva não está conectada.")
            return

        # LED ativo
        self.led.set_state("active")

        # Configura modo
        mode = self.mode_var.get()
        self.calib.set_mode(mode)

        if mode == "cycles":
            try:
                num_cycles = int(self.entry_cycles.get())
                duration = float(self.entry_duration.get())
            except ValueError:
                messagebox.showerror("Erro", "Parâmetros inválidos.")
                return

            self.calib.set_cycle_parameters(num_cycles, duration)

        # Sensores ativos
        self.calib.set_disabled_sensors(self.sensor_list.get_disabled_mask())

        # Inicia calibração
        self.calib.start()

    # Chamado continuamente pelo app (ClinicalGloveApp.check_data)
    def process_glove_data(self, data_str):
        """
        Recebe (gesture_id, values) a partir de ClinicalGloveApp.check_data.
        Compatível também com a versão antiga que envia string bruta.
        """
        try:
            if isinstance(data_str, str):
                parts = data_str.split(",")
                vals = [float(v) for v in parts[1:]]
            else:
                # Esperado: (gesture_id, values)
                _, vals = data_str
        except Exception:
            return

        # Atualiza o modo de calibração com os valores atuais
        try:
            self.calib.update(vals)
        except Exception:
            pass

        # Atualiza exibição dos sensores
        thresholds = self.app.calibration_data.get("sensor_threshold")
        active_mask = None
        # Se o objeto de calibração expõe disabled_mask (True = desabilitado)
        if hasattr(self.calib, "disabled_mask"):
            active_mask = [not bool(x) for x in self.calib.disabled_mask]

        try:
            self.sensor_list.update_values(vals, thresholds=thresholds, active_mask=active_mask)
        except Exception:
            # Falhas na UI não devem quebrar o loop de dados
            return

    # ============================================================
    # CALLBACKS DO CalibrationMode
    # ============================================================
    def on_cycle_start(self, n):
        self.progress["value"] = 0

    def on_cycle_progress(self, progress_01):
        self.progress["value"] = progress_01 * 100

    def on_cycle_end(self, n):
        self.progress["value"] = 100

    def on_continuous_update(self, mins, maxs):
        # Aqui você pode exibir num gráfico futuramente
        pass

    def on_finish(self, results):
        self.led.set_state("ok")
        self.app.calibration_data = results  # salvar no app
        messagebox.showinfo("Concluído", "Calibração finalizada!")

    # ============================================================
    # DIALOGO E SALVAMENTO DE SESSÃO
    # ============================================================
    def show_save_dialog(self):
        """Mostra um modal para preencher nome do paciente e idade, e salva JSON."""
        dlg = tk.Toplevel(self)
        dlg.title("Salvar Sessão de Calibração")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(dlg, text="Nome do Paciente:", anchor="w").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        entry_name = tk.Entry(dlg, width=40)
        entry_name.grid(row=0, column=1, padx=12, pady=(12, 4))

        tk.Label(dlg, text="Idade:", anchor="w").grid(row=1, column=0, padx=12, pady=4, sticky="w")
        entry_age = tk.Entry(dlg, width=10)
        entry_age.grid(row=1, column=1, padx=12, pady=4, sticky="w")

        tk.Label(dlg, text="Observações (opcional):", anchor="w").grid(row=2, column=0, padx=12, pady=4, sticky="nw")
        txt_notes = tk.Text(dlg, width=40, height=5)
        txt_notes.grid(row=2, column=1, padx=12, pady=4)

        def _on_save():
            name = entry_name.get().strip()
            age_text = entry_age.get().strip()
            notes = txt_notes.get("1.0", "end").strip()

            if not name:
                messagebox.showwarning("Dados incompletos", "Informe o nome do paciente.")
                return

            try:
                age = int(age_text) if age_text else None
            except ValueError:
                messagebox.showwarning("Idade inválida", "Idade deve ser um número inteiro.")
                return

            # obter dados de calibração (usar compute_results se disponível)
            try:
                if hasattr(self.calib, "compute_results"):
                    calib_results = self.calib.compute_results()
                else:
                    calib_results = dict(self.app.calibration_data)
            except Exception:
                calib_results = dict(self.app.calibration_data)

            payload = {
                "patient_name": name,
                "age": age,
                "notes": notes,
                "timestamp": datetime.datetime.now().isoformat(),
                "calibration": calib_results
            }

            # criar pasta data/sessions (assume cwd = project modular/)
            sessions_dir = os.path.join(os.getcwd(), "data", "sessions")
            os.makedirs(sessions_dir, exist_ok=True)

            # arquivo: timestamp_nome.json (nome sanitizado)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", name)[:40]
            fname = f"{ts}_{safe_name}.json"
            fpath = os.path.join(sessions_dir, fname)

            try:
                with open(fpath, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
            except Exception as e:
                messagebox.showerror("Erro ao salvar", f"Não foi possível salvar a sessão:\n{e}")
                return

            messagebox.showinfo("Sessão salva", f"Sessão salva em:\n{fpath}")
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(8, 12))
        tk.Button(btn_frame, text="Cancelar", command=dlg.destroy).pack(side="right", padx=6)
        tk.Button(btn_frame, text="Salvar", bg="#06b6d4", fg="white", command=_on_save).pack(side="right", padx=6)

        entry_name.focus_set()
        self.wait_window(dlg)

    # ============================================================
    # NAVEGAÇÃO
    # ============================================================
    def update_glove_status(self, connected: bool):
        self.led.set_state("conectado" if connected else "desconectado")

    def go_to_results(self):
        self.app.show_results_screen(self.app.calibration_data)
