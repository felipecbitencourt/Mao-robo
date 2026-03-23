import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRASH DO SISTEMA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
