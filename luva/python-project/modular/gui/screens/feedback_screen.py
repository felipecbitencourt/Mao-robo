import os
import tkinter as tk
from tkinter import ttk

from gui.widgets.sensor_list import SensorList
from gui.widgets.led_indicator import LEDIndicator
from gui.widgets.vector_viewer import OpenGLCanvas
from gui.widgets.frequency_plot import FrequencyPlot
from gui.widgets.gestos_feedback import GestosFeedback

from core.data_processing import (
    extract_gesture_state,
    compute_vector,
    compute_frequency
)


class FeedbackScreen(tk.Frame):
    """Tela de feedback em tempo real integrada com processamento e visualização."""

    def __init__(self, master, app):
        super().__init__(master, bg="#f0f4f8")
        self.app = app

        # Buffer para análise de frequência
        self.freq_buffer = []

        # Caminho absoluto para assets/models/hand.obj
        self.model_path = self._resolve_model_path("hand.obj")

        self.pack(expand=True, fill="both")
        self.build_ui()

    # ============================================================
    # RESOLVER CAMINHO DO OBJ (CORRIGIDO)
    # ============================================================
    def _resolve_model_path(self, filename: str):
        """
        Resolve o caminho absoluto para assets/models/<filename>,
        independente de onde o script é executado.
        """
        # modular/gui/screens/feedback_screen.py → sobe 3 níveis até modular/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # allow environment override first
        env_model = os.environ.get("BRAIN_GLOVE_MODEL", "").strip()
        if env_model:
            env_model_path = os.path.abspath(env_model)
            if os.path.exists(env_model_path):
                print("\n✅ Modelo 3D (env) carregado de:", env_model_path)
                return env_model_path
            else:
                print("\n⚠️ BRAIN_GLOVE_MODEL definido mas não encontrado:", env_model_path)

        # check alternate models directory (contains textures + rigged files)
        models_hand_dir = os.path.join(base_dir, "assets", "models_hand")
        # default candidates directory
        models_dir = os.path.join(base_dir, "assets", "models")

        # prefer the new models_hand folder if present
        if os.path.isdir(models_hand_dir):
            # more flexible lookup: prefer exact match, then filename substring, then any .obj
            def _find_candidate_in_dir(dirpath, target_name):
                try:
                    files = os.listdir(dirpath)
                except Exception:
                    return None
                name_only, _ = os.path.splitext(target_name)
                # filter obj files first
                obj_files = [f for f in files if f.lower().endswith('.obj')]
                # 1) exact (case-insensitive)
                for f in obj_files:
                    if f.lower() == target_name.lower():
                        return os.path.abspath(os.path.join(dirpath, f))
                # 2) filename contains base name (e.g. 'rigged hand.obj' contains 'hand')
                for f in obj_files:
                    if name_only.lower() in f.lower():
                        return os.path.abspath(os.path.join(dirpath, f))
                # 3) fallback: first .obj in the directory
                if obj_files:
                    return os.path.abspath(os.path.join(dirpath, obj_files[0]))
                return None

            try:
                candidate = _find_candidate_in_dir(models_hand_dir, filename)
                if candidate:
                    print("\n✅ Modelo 3D encontrado em models_hand (best match):", candidate)
                    return candidate
            except Exception:
                pass

        # first: try flexible lookup in default models dir (exact match -> contains -> any .obj)
        def _find_candidate_in_dir_outer(dirpath, target_name):
            try:
                files = os.listdir(dirpath)
            except Exception:
                return None
            name_only, _ = os.path.splitext(target_name)
            obj_files = [f for f in files if f.lower().endswith('.obj')]
            for f in obj_files:
                if f.lower() == target_name.lower():
                    return os.path.abspath(os.path.join(dirpath, f))
            for f in obj_files:
                if name_only.lower() in f.lower():
                    return os.path.abspath(os.path.join(dirpath, f))
            if obj_files:
                return os.path.abspath(os.path.join(dirpath, obj_files[0]))
            return None

        try:
            candidate = _find_candidate_in_dir_outer(models_dir, filename)
            if candidate:
                print("\n✅ Modelo 3D encontrado (best match in models):", candidate)
                return candidate
        except Exception:
            pass

        # next: prefer a smooth variant if it exists (hand_smooth.obj)
        name, ext = os.path.splitext(filename)
        smooth_name = f"{name}_smooth{ext}"
        smooth_path = os.path.abspath(os.path.join(models_dir, smooth_name))
        if os.path.exists(smooth_path):
            print("\n✅ Modelo 3D suave encontrado, usando:", smooth_path)
            return smooth_path

        # fallback: use the exact constructed path (may still succeed on case-insensitive FS)
        model_path = os.path.abspath(os.path.join(models_dir, filename))
        if os.path.exists(model_path):
            print("\n✅ Modelo 3D carregado de:", model_path)
            return model_path

        # nothing found
        print("\n❌ ERRO: Nenhum modelo 3D encontrado em:", models_dir)
        return model_path

    # ============================================================
    # UI
    # ============================================================
    def build_ui(self):
        title = tk.Label(
            self, text="Feedback em Tempo Real",
            font=("Helvetica", 20, "bold"),
            bg="#f0f4f8", fg="#1a202c"
        )
        title.pack(pady=20)

        # LED
        self.led = LEDIndicator(self, label="Status da Luva", initial_state="ok")
        self.led.pack(pady=5)

        # Layout principal
        main = tk.Frame(self, bg="#f0f4f8")
        main.pack(expand=True, fill="both", padx=20, pady=20)

        # ============================================================
        # COLUNA ESQUERDA
        # ============================================================
        left = tk.Frame(main, bg="white", relief="raised", borderwidth=2)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left, text="Visualização do Vetor",
            font=("Helvetica", 15, "bold"),
            bg="white"
        ).pack(pady=5)

        # Widget de gesto
        imgs = getattr(self.app, "gesture_images", None)
        self.gesto_view = GestosFeedback(left, size=320, images=imgs)
        self.gesto_view.pack(pady=6)

        # Viewer 3D (OpenGL) - criado sob demanda por botão
        self._3d_btn = tk.Button(
            left, text="Visualização 3D",
            font=("Helvetica", 12, "bold"),
            bg="#374151", fg="white",
            padx=10, pady=6,
            command=self.open_3d_view
        )
        self._3d_btn.pack(pady=6)

        tk.Label(
            left, text="Análise de Frequência",
            font=("Helvetica", 15, "bold"),
            bg="white"
        ).pack(pady=10)

        self.frequency_plot = FrequencyPlot(left)
        self.frequency_plot.pack(fill="x", padx=10, pady=10)

        # ============================================================
        # COLUNA DIREITA
        # ============================================================
        right = tk.Frame(main, bg="white", relief="raised", borderwidth=2)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(
            right, text="Sensores",
            font=("Helvetica", 16, "bold"), bg="white"
        ).pack(pady=10)

        self.sensor_list = SensorList(
            right,
            sensor_values=[0] * self.app.num_sensors,
            thresholds=self.app.calibration_data.get("sensor_threshold")
        )
        self.sensor_list.pack(expand=True, fill="both", padx=10, pady=10)

        # Botão final
        tk.Button(
            self, text="Finalizar Sessão",
            font=("Helvetica", 14, "bold"),
            bg="#EF4444", fg="white",
            padx=30, pady=10,
            command=self.finish_session
        ).pack(pady=20)

    # ============================================================
    # PROCESSAMENTO DO STREAM
    # ============================================================
    def process_glove_data(self, raw_data):
        """
        Processa a leitura vinda de ClinicalGloveApp.check_data().
        """
        # -----------------------------
        # 1. Compatibilidade com formato antigo ou novo
        # -----------------------------
        try:
            if isinstance(raw_data, str):
                parts = raw_data.split(",")
                vals = [float(v) for v in parts[1:]]
                gesture_id = parts[0] if parts else None
            else:
                gesture_id, vals = raw_data
        except Exception:
            return

        # -----------------------------
        # 2. Atualização de gesto (imagem + label)
        # -----------------------------
        try:
            gid = None
            if gesture_id is not None:
                try:
                    gid = int(gesture_id)
                except Exception:
                    gid = None

            thresholds = self.app.calibration_data.get("sensor_threshold")

            try:
                gesture_state = extract_gesture_state(vals, thresholds)
            except Exception:
                gesture_state = None

            label_text = (
                f"Gesto: {gesture_state}"
                if gesture_state is not None else None
            )

            self.gesto_view.update_from_values(
                gid, vals, label_text=label_text
            )

        except Exception:
            pass

        # -----------------------------
        # 3. Atualiza lista de sensores
        # -----------------------------
        try:
            thresholds = self.app.calibration_data.get("sensor_threshold")
            self.sensor_list.update_values(vals, thresholds=thresholds)
        except Exception:
            pass

        # -----------------------------
        # 4. Atualiza vetor no OpenGL (rotaciona a mão)
        # -----------------------------
        try:
            vec = compute_vector(vals)
            if hasattr(self, "vector_viewer") and self.vector_viewer is not None:
                try:
                    self.vector_viewer.update_vector(vec)
                except Exception:
                    # if the viewer fails, ignore so the stream continues
                    pass
        except Exception:
            pass

        # -----------------------------
        # 5. Atualiza análise de frequência
        # -----------------------------
        try:
            self.freq_buffer.append(vals)
            if len(self.freq_buffer) > 128:
                self.freq_buffer.pop(0)

            freq = compute_frequency(self.freq_buffer)
            if freq is not None:
                self.frequency_plot.update(freq)
        except Exception:
            pass

    # ============================================================
    # FINALIZAÇÃO
    # ============================================================
    def update_glove_status(self, connected: bool):
        """Atualiza LED de status da conexão."""
        self.led.set_state("ok" if connected else "error")

    def finish_session(self):
        """Retorna à tela inicial."""
        self.app.show_main_screen()

    # ============================================================
    # 3D VIEW WINDOW HANDLING
    # ============================================================
    def open_3d_view(self):
        """Abre uma janela Toplevel com o `OpenGLCanvas` se ainda não existir."""
        # if already opened, bring to front
        if getattr(self, "opengl_window", None) is not None:
            try:
                if self.opengl_window.winfo_exists():
                    self.opengl_window.lift()
                    return
            except Exception:
                # fallthrough to recreate
                pass

        # create window
        self.opengl_window = tk.Toplevel(self)
        self.opengl_window.title("Visualização 3D")
        # reasonable default size; user can resize
        try:
            self.opengl_window.geometry("800x600")
        except Exception:
            pass
        self.opengl_window.protocol("WM_DELETE_WINDOW", self.close_3d_view)

        # create the OpenGL canvas inside the Toplevel
        try:
            self.vector_viewer = OpenGLCanvas(self.opengl_window, obj_path=self.model_path)
            self.vector_viewer.pack(expand=True, fill="both")
        except Exception as e:
            message = f"Falha ao criar visualização 3D: {e}"
            try:
                messagebox.showerror("Erro", message)
            except Exception:
                print(message)
            # ensure clean state
            try:
                self.opengl_window.destroy()
            except Exception:
                pass
            self.opengl_window = None
            self.vector_viewer = None
            return

        # disable button to avoid duplicate windows
        try:
            self._3d_btn.config(state="disabled")
        except Exception:
            pass

    def close_3d_view(self):
        """Fecha a janela 3D e libera referências."""
        try:
            if getattr(self, "opengl_window", None) is not None:
                try:
                    self.opengl_window.destroy()
                except Exception:
                    pass
        finally:
            self.opengl_window = None
            self.vector_viewer = None
            try:
                self._3d_btn.config(state="normal")
            except Exception:
                pass
