import sys
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette, QIcon, QFont
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QSplitter, QGraphicsDropShadowEffect, QLineEdit, QProgressBar)

from core.hub_controller import HubController
from ui.components.video_display import VideoDisplay
from ui.components.gesture_display import GestureDisplay
from ui.components.custom_buttons import ActionButton, AnimatedButton

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hub = HubController()
        self.setWindowTitle("Mão Robótica Pro - Hub Multimodal")
        self.resize(1100, 800)
        
        # Conexão de sinais do controlador
        self.hub.status_signal.connect(self.update_status_bar)
        self.hub.prediction_signal.connect(self.update_prediction)
        self.hub.glove_signal.connect(self.update_glove_data)
        self.hub.eeg_signal.connect(self.update_eeg_data)
        
        self._init_ui()

    def start_calibration_sequence(self):
        """Inicia a sequência de 3 passos: FECHADO -> MEIO -> ABERTO"""
        self.btn_calibrate_glove.setEnabled(False)
        self.hub.status_signal.emit("Iniciando calibração em 3 passos...")
        
        # Passo 1: FECHADO
        self._run_calib_step("FECHE A MÃO COMPLETAMENTE", "CLOSED", 0)
        
        # Passo 2: MEIO (após 4s = 1s prep + 3s coleta)
        QTimer.singleShot(4000, lambda: self._run_calib_step("MANTENHA A MÃO RELAXADA (MEIO)", "HALF", 1))
        
        # Passo 3: ABERTO (após 8s)
        QTimer.singleShot(8000, lambda: self._run_calib_step("ABRA A MÃO COMPLETAMENTE", "OPEN", 2))
        
        # Finalização (após 12s)
        QTimer.singleShot(12000, self.finish_calibration_ui)

    def _run_calib_step(self, msg, state, step_idx):
        print(f"DEBUG UI: Passo {step_idx} - {state}")
        self.result_label.setText(msg)
        self.result_label.setStyleSheet("font-size: 24px; color: #F59E0B; font-weight: bold;")
        
        # 1 segundo de preparação, depois 3 segundos de coleta
        QTimer.singleShot(1000, lambda: self.hub.start_glove_calibration(state))
        QTimer.singleShot(4000, lambda: self.hub.finish_glove_calibration_step())

    def finish_calibration_ui(self):
        self.btn_calibrate_glove.setEnabled(True)
        self.result_label.setText("CALIBRAÇÃO CONCLUÍDA")
        self.result_label.setStyleSheet("font-size: 32px; color: #10B981; font-weight: bold;")
        self.hub.status_signal.emit("Luva calibrada com sucesso!")
        # Volta ao estilo normal após 2 segundos
        QTimer.singleShot(2000, lambda: self.result_label.setStyleSheet("font-size: 32px; color: #FFFFFF; font-weight: bold;"))

    def closeEvent(self, event):
        """Garante que todas as threads sejam paradas ao fechar a janela"""
        print("Fechando aplicação... parando threads.")
        self.hub.stop()
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
        self.btn_cam.setCheckable(True)
        self.btn_cam.toggled.connect(self._toggle_camera)
        sidebar_layout.addWidget(self.btn_cam)
        
        self.btn_glove = AnimatedButton("🧤 LUVA 5DT", accent_color="#10B981")
        self.btn_glove.setCheckable(True)
        self.btn_glove.toggled.connect(self._toggle_glove)
        sidebar_layout.addWidget(self.btn_glove)
        
        self.btn_eeg = AnimatedButton("🧠 EEG BRAINLINK", accent_color="#F59E0B")
        self.btn_eeg.setCheckable(True)
        self.btn_eeg.toggled.connect(self._toggle_eeg)
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
        self.btn_test_hand.clicked.connect(self.hub.test_arduino_hand)
        sidebar_layout.addWidget(self.btn_test_hand)

        self.btn_auto_ports = AnimatedButton("🔍 DETECTAR PORTAS", accent_color="#8B5CF6")
        self.btn_auto_ports.clicked.connect(self.hub.auto_detect_all_ports)
        sidebar_layout.addWidget(self.btn_auto_ports)
        
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
        self.hub.frame_signal.connect(self.video_display.update_frame)
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
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.gesture_display = GestureDisplay(images_path=os.path.join(base_dir, "luva", "gesture-images"))
        data_layout.addWidget(self.gesture_display)
        
        text_data_layout = QVBoxLayout()
        
        # Nome do Gesto e Fonte
        self.result_label = QLabel("AGUARDANDO GESTO")
        self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #FFFFFF;")
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_data_layout.addWidget(self.result_label)
        
        self.source_label = QLabel("Fonte: -")
        self.source_label.setStyleSheet("color: #E94560; font-weight: bold; font-size: 14px; text-transform: uppercase;")
        text_data_layout.addWidget(self.source_label)
        
        # Telemetria da Luva (Barras de progresso horizontais)
        self.glove_telemetry = QFrame()
        glove_tel_layout = QVBoxLayout(self.glove_telemetry)
        glove_tel_layout.setContentsMargins(0, 5, 0, 5)
        self.glove_bars = []
        for i in range(5):
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar {
                    background-color: #2A2A40;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background-color: #10B981;
                    border-radius: 4px;
                }
            """)
            self.glove_bars.append(bar)
            glove_tel_layout.addWidget(bar)
        self.glove_telemetry.hide()
        text_data_layout.addWidget(self.glove_telemetry)
        
        # Botão de Calibração
        self.btn_calibrate_glove = QPushButton("CALIBRAR LUVA")
        self.btn_calibrate_glove.setFixedHeight(30)
        self.btn_calibrate_glove.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        self.btn_calibrate_glove.clicked.connect(self.start_calibration_sequence)
        text_data_layout.addWidget(self.btn_calibrate_glove)

        # Telemetria EEG
        self.eeg_telemetry = QFrame()
        eeg_tel_layout = QVBoxLayout(self.eeg_telemetry)
        
        # Atenção
        attn_layout = QHBoxLayout()
        attn_layout.addWidget(QLabel("ATT:"))
        self.attn_bar = QProgressBar()
        self.attn_bar.setFixedHeight(12)
        self.attn_bar.setRange(0, 100)
        self.attn_bar.setTextVisible(True)
        self.attn_bar.setStyleSheet("""
            QProgressBar { background-color: #2A2A40; border-radius: 6px; color: white; text-align: center; }
            QProgressBar::chunk { background-color: #EF4444; border-radius: 6px; }
        """)
        attn_layout.addWidget(self.attn_bar)
        eeg_tel_layout.addLayout(attn_layout)
        
        # Meditação
        med_layout = QHBoxLayout()
        med_layout.addWidget(QLabel("MED:"))
        self.med_bar = QProgressBar()
        self.med_bar.setFixedHeight(12)
        self.med_bar.setRange(0, 100)
        self.med_bar.setTextVisible(True)
        self.med_bar.setStyleSheet("""
            QProgressBar { background-color: #2A2A40; border-radius: 6px; color: white; text-align: center; }
            QProgressBar::chunk { background-color: #3B82F6; border-radius: 6px; }
        """)
        med_layout.addWidget(self.med_bar)
        eeg_tel_layout.addLayout(med_layout)

        self.eeg_label = QLabel("SINAL: -")
        self.eeg_label.setStyleSheet("color: #F59E0B; font-family: 'Consolas'; font-size: 11px;")
        eeg_tel_layout.addWidget(self.eeg_label)
        
        self.eeg_telemetry.hide()
        text_data_layout.addWidget(self.eeg_telemetry)
        
        data_layout.addLayout(text_data_layout)
        
        central_layout.addWidget(self.data_panel)
        
        # --- PAINEL DE CONTROLE (Dashboard Inferior) ---
        self.control_panel = QHBoxLayout()
        self.control_panel.setSpacing(20)
        
        self.btn_start = ActionButton("INICIAR MOTOR", color="#10B981")
        self.btn_start.clicked.connect(self.hub.start)
        
        self.btn_stop = ActionButton("PARAR TUDO", color="#EF4444")
        self.btn_stop.clicked.connect(self.hub.stop)
        
        self.btn_calibrate = ActionButton("CALIBRAR", color="#3B82F6")
        self.btn_calibrate.clicked.connect(self.hub.calibrate)
        
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
        if self.hub.arduino:
            self.hub.arduino.port = text
            print(f"DEBUG HUB: Porta alterada para {text}")

    def _toggle_output_hand(self, checked):
        if checked:
            self.btn_output_hand.setText("🦾 MÃO ROBÓTICA: ON")
            self.btn_output_hand.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; border-radius: 8px;")
            self.hub.set_hand_output(True)
        else:
            self.btn_output_hand.setText("🦾 MÃO ROBÓTICA: OFF")
            self.btn_output_hand.setStyleSheet("background-color: #0f3460; color: white; border-radius: 8px;")
            self.hub.set_hand_output(False)

    def _toggle_camera(self, checked):
        if checked:
            self.btn_cam.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
            self.hub.set_camera_active(True)
        else:
            self.btn_cam.setStyleSheet("") # Volta ao estilo original do AnimatedButton
            self.hub.set_camera_active(False)

    def _toggle_glove(self, checked):
        if checked:
            self.btn_glove.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
            self.hub.set_glove_active(True)
        else:
            self.btn_glove.setStyleSheet("")
            self.hub.set_glove_active(False)

    def _toggle_eeg(self, checked):
        if checked:
            self.btn_eeg.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
            self.hub.set_eeg_active(True)
        else:
            self.btn_eeg.setStyleSheet("")
            self.hub.set_eeg_active(False)

    def update_status_bar(self, message):
        self.status_bar_label.setText(f"📡 {message.upper()}")

    def update_glove_data(self, data):
        self.glove_telemetry.show()
        sensors = data.get("sensors", [])
        for i, val in enumerate(sensors[:5]):
            if i < len(self.glove_bars):
                # val costuma ser 0-1.0. 
                self.glove_bars[i].setValue(int(val * 100))
                # Cor dinâmica 
                color = "#10B981" if val < 0.5 else "#F59E0B"
                self.glove_bars[i].setStyleSheet(f"""
                    QProgressBar {{ background-color: #2A2A40; border-radius: 4px; }}
                    QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}
                """)

    def update_prediction(self, data):
        gid = data.get("gesture_id", -1)
        pred = data.get("prediction", "N/A")
        conf = data.get("confidence", 0)
        source = data.get("source", "UNKNOWN")
        
        print(f"*** UI RECEIVE: {pred} FROM {source} ***")
        
        self.result_label.setText(f"{pred}")
        self.source_label.setText(f"FONTE: {source} ({conf}%)")
        self.gesture_display.update_gesture(gid)
        
        # Muda a cor dinamicamente se a confiança for alta
        if conf > 85:
            self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #10B981;")
        else:
            self.result_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #FFFFFF;")

    def update_eeg_data(self, data):
        self.eeg_telemetry.show()
        att = data.get("attention", 0)
        med = data.get("meditation", 0)
        sig = data.get("signal", 200)
        
        self.attn_bar.setValue(att)
        self.med_bar.setValue(med)
        
        status_text = "BOM" if sig < 50 else ("FALHANDO" if sig < 200 else "SEM SINAL")
        self.eeg_label.setText(f"SINAL: {sig:3d} ({status_text})")
        
        # Altera cor se sinal for ruim
        if sig > 50:
            self.eeg_label.setStyleSheet("color: #EF4444; font-family: 'Consolas'; font-size: 11px;")
        else:
            self.eeg_label.setStyleSheet("color: #10B981; font-family: 'Consolas'; font-size: 11px;")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
