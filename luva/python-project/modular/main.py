"""
main.py
Ponto de entrada do sistema de neuroreabilitação com a luva 5DT.
Gerencia inicialização da UI, logging e captura global de erros.
"""

import sys
import logging
import tkinter as tk
from tkinter import messagebox
from gui.clinical_glove_app import ClinicalGloveApp


# ============================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================
def setup_logging():
    logging.basicConfig(
        filename="app.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filemode="a"
    )
    logging.info("Aplicação iniciada.")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    setup_logging()

    try:
        # Janela principal
        root = tk.Tk()
        root.title("Luva 5DT - Sistema de Neuroreabilitação")

        # 🔹 Ajuste automático à resolução da tela
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        app_width = int(screen_width * 0.90)
        app_height = int(screen_height * 0.90)

        x = (screen_width // 2) - (app_width // 2)
        y = (screen_height // 2) - (app_height // 2)

        root.geometry(f"{app_width}x{app_height}+{x}+{y}")
        root.minsize(900, 600)  # segurança para notebooks

        # Inicializa o app
        app = ClinicalGloveApp(root)

        logging.info("Interface carregada com sucesso.")

        root.mainloop()

    except Exception as e:
        logging.exception("Erro crítico durante execução:")
        messagebox.showerror("Erro Fatal", f"Ocorreu um erro crítico:\n{e}")
        sys.exit(1)


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================
if __name__ == "__main__":
    main()
