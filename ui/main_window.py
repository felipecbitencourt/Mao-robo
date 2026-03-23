import sys
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette, QIcon, QFont
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QSplitter, QGraphicsDropShadowEffect, QLineEdit)

from core.hub_controller import HubController
from ui.components.video_display import VideoDisplay
from ui.components.gesture_display import GestureDisplay
from ui.components.custom_buttons import ActionButton, AnimatedButton

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = HubController()
        self.setWindowTitle("Mão Robótica Pro - Hub Multimodal")
        self.resize(1100, 800)
        
        # Conexão de sinais do controlador
        self.controller.status_signal.connect(self.update_status_bar)
        self.controller.prediction_signal.connect(self.update_prediction)
        self.controller.glove_signal.connect(self.update_glove_data)
        
        self._init_ui()

    def closeEvent(self, event):
        """Garante que todas as threads sejam paradas ao fechar a janela"""
        print("Fechando aplicação... parando threads.")
        self.controller.stop()
        event.accept()

    def _init_ui(self):
        # Estilo Global
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: #BDBDBD;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#sidebar {
                background-color: #1E1E2F;
                border-right: 1px solid #2A2A40;
            }
            QFrame#central_content {
                background-color: #121212;
            }
            QFrame#status_panel {
                background-color: #1A1A2E;
                border: 1px solid #2A2A40;
                border-radius: 12px;
            }
        """)

        # Widget Central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(15)
        
        sidebar_title = QLabel("HUB CONTROL")
        sidebar_title.setStyleSheet("font-weight: bold; font-size: 22px; color: #E94560; margin-bottom: 20px;")
        sidebar_layout.addWidget(sidebar_title)
        
        # Dispositivos
        sidebar_layout.addWidget(QLabel("INPUTS DISPONÍVEIS"))
        
        self.btn_cam = AnimatedButton("🎥 CÂMERA", accent_color="#3B82F6")
        self.btn_cam.clicked.connect(self.controller.connect_devices)
        sidebar_layout.addWidget(self.btn_cam)
        
        self.btn_glove = AnimatedButton("🧤 LUVA 5DT", accent_color="#10B981")
        sidebar_layout.addWidget(self.btn_glove)
        
        self.btn_eeg = AnimatedButton("🧠 EEG BRAINLINK", accent_color="#F59E0B")
        sidebar_layout.addWidget(self.btn_eeg)

        sidebar_layout.addSpacing(30)
        
        # Seção de Saída
        sidebar_layout.addWidget(QLabel("CONTROLE DE SAÍDA"))
        
        # Campo para Porta COM
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Porta:"))
        self.port_edit = QLineEdit("COM5")
        self.port_edit.setStyleSheet("background-color: #1A1A2E; color: white; padding: 5px;")
        self.port_edit.textChanged.connect(self._update_port)
        port_layout.addWidget(self.port_edit)
        sidebar_layout.addLayout(port_layout)

        self.btn_output_hand = AnimatedButton("🦾 MÃO ROBÓTICA: OFF", accent_color="#EF4444")
        self.btn_output_hand.setCheckable(True)
        self.btn_output_hand.toggled.connect(self._toggle_output_hand)
        sidebar_layout.addWidget(self.btn_output_hand)
        
        self.btn_test_hand = AnimatedButton("⚙️ TESTAR SERVOS", accent_color="#3B82F6")
        self.btn_test_hand.clicked.connect(self.controller.test_arduino_hand)
        sidebar_layout.addWidget(self.btn_test_hand)
        
        sidebar_layout.addStretch()
        
        # --- ÁREA CENTRAL ---
        self.central_content = QFrame()
        self.central_content.setObjectName("central_content")
        central_layout = QVBoxLayout(self.central_content)
        central_layout.setContentsMargins(30, 30, 30, 30)
        central_layout.setSpacing(25)
        
        # Painel de Vídeo (Visualização)
        self.video_container = QFrame()
        self.video_container.setObjectName("status_panel")
        self.video_container.setMinimumHeight(350)
        video_layout = QVBoxLayout(self.video_container)
        
        self.video_display = VideoDisplay()
        self.controller.frame_signal.connect(self.video_display.update_frame)
        video_layout.addWidget(self.video_display)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.video_container.setGraphicsEffect(shadow)
        
        central_layout.addWidget(self.video_container)
        
        # Painel de Dados em Tempo Real
        self.data_panel = QFrame()
        self.data_panel.setObjectName("status_panel")
        data_layout = QHBoxLayout(self.data_panel) # Mudei para Horizontal para caber a imagem ao lado
        
        # Lado Esquerdo: Imagem do Gesto
        self.gesture_display = GestureDisplay()
        data_layout.addWidget(self.gesture_display)
        
        # Lado Direito: Textos
        text_data_layout = QVBoxLayout()
        self.result_label = QLabel("AGUARDANDO GESTO")
        self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #FFFFFF;")
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_data_layout.addWidget(self.result_label)
        
        self.glove_label = QLabel("Dados: (-) ")
        self.glove_label.setStyleSheet("color: #888888; font-family: 'Consolas'; font-size: 14px;")
        text_data_layout.addWidget(self.glove_label)
        
        data_layout.addLayout(text_data_layout)
        
        central_layout.addWidget(self.data_panel)
        
        # --- PAINEL DE CONTROLE (Dashboard Inferior) ---
        self.control_panel = QHBoxLayout()
        self.control_panel.setSpacing(20)
        
        self.btn_start = ActionButton("INICIAR MOTOR", color="#10B981")
        self.btn_start.clicked.connect(self.controller.start)
        
        self.btn_stop = ActionButton("PARAR TUDO", color="#EF4444")
        self.btn_stop.clicked.connect(self.controller.stop)
        
        self.btn_calibrate = ActionButton("CALIBRAR", color="#3B82F6")
        self.btn_calibrate.clicked.connect(self.controller.calibrate)
        
        self.control_panel.addWidget(self.btn_start)
        self.control_panel.addWidget(self.btn_stop)
        self.control_panel.addWidget(self.btn_calibrate)
        
        central_layout.addLayout(self.control_panel)
        
        # Barra de Status
        self.status_bar_label = QLabel("SISTEMA PRONTO")
        self.status_bar_label.setStyleSheet("padding: 10px; border-top: 1px solid #2A2A40;")
        central_layout.addWidget(self.status_bar_label)

        # Montagem Final
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.central_content)

    def _update_port(self, text):
        """Atualiza a porta serial dinamicamente"""
        if self.controller.arduino:
            self.controller.arduino.port = text
            print(f"DEBUG HUB: Porta alterada para {text}")

    def _toggle_output_hand(self, checked):
        if checked:
            self.btn_output_hand.setText("🦾 MÃO ROBÓTICA: ON")
            self.btn_output_hand.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; border-radius: 8px;")
            self.controller.set_hand_output(True)
        else:
            self.btn_output_hand.setText("🦾 MÃO ROBÓTICA: OFF")
            self.btn_output_hand.setStyleSheet("background-color: #0f3460; color: white; border-radius: 8px;")
            self.controller.set_hand_output(False)

    def update_status_bar(self, message):
        self.status_bar_label.setText(f"📡 {message.upper()}")

    def update_glove_data(self, data):
        gid = data.get("gesture_id", -1)
        sensors = data.get("sensors", [])
        sensor_str = " | ".join([f"{v:.2f}" for v in sensors[:5]])
        self.glove_label.setText(f"🧤 GESTO {gid} | SENSORES: {sensor_str}")

    def update_prediction(self, data):
        gid = data.get("gesture_id", -1)
        pred = data.get("prediction", "N/A")
        conf = data.get("confidence", 0)
        
        self.result_label.setText(f"{pred} ({conf}%)")
        self.gesture_display.update_gesture(gid)
        
        # Muda a cor dinamicamente se a confiança for alta
        if conf > 85:
            self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #10B981;")
        else:
            self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #FFFFFF;")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
