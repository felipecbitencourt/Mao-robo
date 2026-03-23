# gui/screens/results_screen.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime


class ResultsScreen(tk.Frame):
    """Tela de resultados após o processo de calibração."""

    def __init__(self, master, app, results_data):
        super().__init__(master, bg="#f0f4f8")
        self.app = app
        self.results_data = results_data
        self.pack(expand=True, fill="both")

        self.build_ui()

    # ============================================================
    # UI
    # ============================================================
    def build_ui(self):
        title = tk.Label(
            self, text="Resultados da Calibração",
            font=("Helvetica", 20, "bold"),
            bg="#f0f4f8", fg="#1a202c"
        )
        title.pack(pady=25)

        # --------------------------
        # Tabela
        # --------------------------
        table_frame = tk.Frame(self, bg="white", relief="raised", borderwidth=2)
        table_frame.pack(expand=True, fill="both", padx=30, pady=20)

        columns = ("Sensor", "Mínimo", "Máximo", "Threshold")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="center")

        self.tree.pack(expand=True, fill="both", padx=10, pady=10)

        # Inserção dos resultados
        self.populate_table()

        # --------------------------
        # Botões
        # --------------------------
        btn_frame = tk.Frame(self, bg="#f0f4f8")
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame, text="← Voltar",
            bg="#6B7280", fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20, pady=8,
            command=self.app.show_calibration_screen
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Salvar Sessão",
            bg="#3B82F6", fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20, pady=8,
            command=self.save_session_dialog
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Iniciar Feedback →",
            bg="#10B981", fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20, pady=8,
            command=self.app.show_feedback_screen
        ).pack(side="left", padx=8)

    # ============================================================
    # POPULAR TABELA
    # ============================================================
    def populate_table(self):
        """Preenche a tabela com os valores calibrados."""
        mins = self.results_data["sensor_min"]
        maxs = self.results_data["sensor_max"]
        ths = self.results_data["sensor_threshold"]

        self.tree.delete(*self.tree.get_children())

        for i, (mn, mx, th) in enumerate(zip(mins, maxs, ths)):
            self.tree.insert("", "end", values=(
                f"Sensor {i+1}",
                f"{mn:.3f}",
                f"{mx:.3f}",
                f"{th:.3f}"
            ))

    # ============================================================
    # EXPORTAÇÃO
    # ============================================================
    def save_session_dialog(self):
        """
        Abre um diálogo modal listando pacientes já existentes (pastas em data/),
        permitindo escolher um existente ou criar um novo usuário. Em seguida
        salva o JSON da sessão dentro da pasta selecionada.
        """
        try:
            # montar os dados da sessão a salvar
            session_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "sensor_min": self.results_data["sensor_min"],
                "sensor_max": self.results_data["sensor_max"],
                "sensor_threshold": self.results_data["sensor_threshold"],
                "num_sensors": len(self.results_data["sensor_min"]),
                "mode": "calibration"
            }

            # base data dir (usar state_manager se disponível)
            base_dir = getattr(getattr(self.app, 'state_manager', None), 'base_dir', None)
            if not base_dir:
                base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            # ensure exists
            os.makedirs(base_dir, exist_ok=True)

            # list patient folders (directories) inside base_dir
            candidates = []
            try:
                for name in os.listdir(base_dir):
                    p = os.path.join(base_dir, name)
                    if os.path.isdir(p):
                        candidates.append(name)
            except Exception:
                candidates = []

            # modal dialog: simple Toplevel with Listbox + buttons
            dlg = tk.Toplevel(self)
            dlg.title("Salvar Sessão - Selecionar Paciente")
            dlg.transient(self.winfo_toplevel())
            dlg.grab_set()
            tk.Label(dlg, text="Escolha paciente existente ou crie novo:", pady=8).pack()

            listbox = tk.Listbox(dlg, height=8, width=40)
            for c in candidates:
                listbox.insert('end', c)
            listbox.pack(padx=12, pady=6)

            btn_row = tk.Frame(dlg)
            btn_row.pack(pady=8)

            def on_select():
                sel = listbox.curselection()
                if not sel:
                    messagebox.showwarning("Selecionar", "Selecione um paciente ou crie novo usuário.")
                    return
                name = listbox.get(sel[0])
                dlg.destroy()
                save_to_patient(name)

            def on_new():
                dlg.withdraw()
                name = simpledialog.askstring("Novo Usuário", "Nome do paciente (sem caracteres especiais):", parent=self)
                dlg.deiconify()
                if not name:
                    return
                # sanitize name (basic)
                safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe:
                    messagebox.showerror("Erro", "Nome inválido para o paciente.")
                    return
                # create folder
                patient_dir = os.path.join(base_dir, safe)
                try:
                    os.makedirs(patient_dir, exist_ok=True)
                except Exception as e:
                    messagebox.showerror("Erro", f"Não foi possível criar pasta do paciente:\n{e}")
                    return
                dlg.destroy()
                save_to_patient(safe)

            def on_cancel():
                dlg.destroy()

            tk.Button(btn_row, text="Selecionar", command=on_select, bg="#3B82F6", fg="white").pack(side="left", padx=6)
            tk.Button(btn_row, text="Novo Usuário", command=on_new, bg="#10B981", fg="white").pack(side="left", padx=6)
            tk.Button(btn_row, text="Cancelar", command=on_cancel, bg="#6B7280", fg="white").pack(side="left", padx=6)

            def save_to_patient(patient_name):
                try:
                    patient_dir = os.path.join(base_dir, patient_name)
                    os.makedirs(patient_dir, exist_ok=True)
                    # filename: timestamp.json
                    fname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
                    path = os.path.join(patient_dir, fname)
                    import json
                    with open(path, "w", encoding="utf-8") as fp:
                        json.dump(session_data, fp, indent=4, ensure_ascii=False)

                    messagebox.showinfo("Sessão salva", f"Sessão salva em:\n{path}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao salvar sessão:\n{e}")

            # center dialog
            self.update_idletasks()
            dlg.geometry(f"+{self.winfo_rootx()+50}+{self.winfo_rooty()+50}")
            dlg.wait_window()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar sessão:\n{e}")
