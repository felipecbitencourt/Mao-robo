# gui/screens/history_screen.py

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox


class HistoryScreen(tk.Frame):
    """
    Tela de histórico de sessões salvas.
    Depende do state_manager para listar e carregar sessões.
    """

    def __init__(self, master, app):
        super().__init__(master, bg="#f0f4f8")
        self.app = app
        self.pack(expand=True, fill="both")

        self.selected_session_path = None

        self.build_ui()
        self.load_session_list()

    # ============================================================
    # UI
    # ============================================================
    def build_ui(self):

        # Título
        tk.Label(
            self,
            text="Histórico de Sessões",
            font=("Helvetica", 20, "bold"),
            bg="#f0f4f8",
            fg="#1a202c"
        ).pack(pady=15)

        # Layout geral
        layout = tk.Frame(self, bg="#f0f4f8")
        layout.pack(fill="both", expand=True, padx=20, pady=10)

        # ------------------------------------------------------------
        # Lista de sessões
        # ------------------------------------------------------------
        list_frame = tk.Frame(layout, bg="white", relief="raised", borderwidth=2)
        list_frame.pack(side="left", fill="y", expand=False, padx=(0, 10))

        tk.Label(
            list_frame,
            text="Sessões Salvas",
            font=("Helvetica", 14, "bold"),
            bg="white"
        ).pack(pady=10)

        self.session_listbox = tk.Listbox(list_frame, height=25, width=35)
        self.session_listbox.pack(padx=10, pady=10, fill="y")
        self.session_listbox.bind("<<ListboxSelect>>", self.on_session_select)

        # ------------------------------------------------------------
        # Painel de detalhes da sessão
        # ------------------------------------------------------------
        details_frame = tk.Frame(layout, bg="white", relief="raised", borderwidth=2)
        details_frame.pack(side="left", fill="both", expand=True)

        tk.Label(
            details_frame,
            text="Detalhes da Sessão",
            font=("Helvetica", 14, "bold"),
            bg="white"
        ).pack(pady=10)

        # Info básica (timestamp, sensores, modo)
        self.info_label = tk.Label(
            details_frame, text="Selecione uma sessão...",
            font=("Helvetica", 12),
            bg="white", justify="left"
        )
        self.info_label.pack(pady=5, anchor="w", padx=15)

        # Tabela dos sensores
        self.tree = ttk.Treeview(
            details_frame,
            columns=("Sensor", "Min", "Max", "Threshold"),
            show="headings",
            height=10
        )
        for col in ("Sensor", "Min", "Max", "Threshold"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        # ------------------------------------------------------------
        # Botões inferiores
        # ------------------------------------------------------------
        btn_frame = tk.Frame(self, bg="#f0f4f8")
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame, text="← Voltar",
            bg="#6B7280", fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20, pady=8,
            command=self.app.show_main_screen
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame, text="Atualizar Lista",
            bg="#3B82F6", fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20, pady=8,
            command=self.load_session_list
        ).pack(side="left", padx=10)

    # ============================================================
    # CARREGAR LISTA DE SESSÕES
    # ============================================================
    def load_session_list(self):
        """Carrega os arquivos JSON em data/sessions."""
        self.session_listbox.delete(0, tk.END)

        sessions_dir = "data/sessions"
        os.makedirs(sessions_dir, exist_ok=True)

        files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]

        if not files:
            self.session_listbox.insert(tk.END, "Nenhuma sessão salva.")
            return

        for f in sorted(files):
            self.session_listbox.insert(tk.END, f)

    # ============================================================
    # AO SELECIONAR UMA SESSÃO
    # ============================================================
    def on_session_select(self, event):
        selection = self.session_listbox.curselection()
        if not selection:
            return

        filename = self.session_listbox.get(selection[0])
        if filename == "Nenhuma sessão salva.":
            return

        path = os.path.join("data/sessions", filename)
        self.selected_session_path = path

        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar:\n{e}")
            return

        self.display_session(data)

    # ============================================================
    # EXIBIR OS DADOS CARREGADOS
    # ============================================================
    def display_session(self, data):
        """Mostra os dados no painel da direita."""

        timestamp = data.get("timestamp", "N/D")
        mode = data.get("mode", "N/D")
        num = data.get("num_sensors", 0)

        info_text = (
            f"📅 Data: {timestamp}\n"
            f"⚙️ Modo: {mode}\n"
            f"🔢 Sensores ativos: {num}\n"
        )

        self.info_label.config(text=info_text)

        # Preenche tabela
        self.tree.delete(*self.tree.get_children())

        mins = data.get("sensor_min", [])
        maxs = data.get("sensor_max", [])
        ths = data.get("sensor_threshold", [])

        for i, (mn, mx, th) in enumerate(zip(mins, maxs, ths)):
            self.tree.insert(
                "", "end",
                values=(f"Sensor {i+1}", f"{mn:.3f}", f"{mx:.3f}", f"{th:.3f}")
            )
