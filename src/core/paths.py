import sys
import os

def resource_path(relative_path):
    """
    Obtém o caminho absoluto para o recurso garantindo a funcionalidade
    tanto em ambiente de desenvolvimento interativo quanto no .exe compilado
    através do PyInstaller (que centraliza tudo na pasta _internal ou _MEIPASS).
    """
    if getattr(sys, 'frozen', False):
        # Em modo '--onedir' (padrão) executáveis PyInstaller 5.0+ jogam assets no "_internal"
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.join(os.path.dirname(sys.executable), "_internal")
    else:
        # Modo Dev: Volta duas pastas porque estamos em src/core/paths.py
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Normalizamos a saída com `normpath` e `join`
    return os.path.normpath(os.path.join(base_path, relative_path))
