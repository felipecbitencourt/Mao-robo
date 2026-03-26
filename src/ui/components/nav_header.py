from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

class NavHeader(QFrame):
    """
    Header de navegação global com indicadores de status e controles de sistema.
    """
    theme_toggled = Signal()
    tab_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nav_header")
        self.setFixedHeight(64)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(24, 0, 24, 0)
        self.layout.setSpacing(20)

        # ── LOGO E TÍTULO ────────────────────────────────────────
        self.logo_label = QLabel("🤖")
        self.logo_label.setStyleSheet("font-size: 24px;")
        self.title_label = QLabel("MÃO-ROBÔ v2.0")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; letter-spacing: 2px; color: #F4F4FD;")
        
        self.title_group = QHBoxLayout()
        self.title_group.setSpacing(12)
        self.title_group.addWidget(self.logo_label)
        self.title_group.addWidget(self.title_label)
        self.layout.addLayout(self.title_group)

        self.layout.addStretch()

        # ── INDICADORES DE STATUS (HUD) ──────────────────────────
        self.hud_container = QFrame()
        self.hud_container.setObjectName("hud_nav")
        self.hud_container.setStyleSheet("""
            QFrame#hud_nav {
                background: rgba(26, 26, 38, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """)
        hud_lyt = QHBoxLayout(self.hud_container)
        hud_lyt.setContentsMargins(15, 6, 15, 6)
        hud_lyt.setSpacing(18)

        self.arduino_indicator = QLabel("● ARDUINO: OFF")
        self.arduino_indicator.setStyleSheet("color:#EF4444; font-weight:bold; font-size:10px;")
        
        self.eeg_indicator = QLabel("● EEG: OFF")
        self.eeg_indicator.setStyleSheet("color:#EF4444; font-weight:bold; font-size:10px;")

        self.fps_indicator = QLabel("● FPS: 0")
        self.fps_indicator.setStyleSheet("color:#7D7D9C; font-weight:bold; font-size:10px;")

        hud_lyt.addWidget(self.arduino_indicator)
        hud_lyt.addWidget(self.eeg_indicator)
        hud_lyt.addWidget(self.fps_indicator)
        self.layout.addWidget(self.hud_container)

        self.layout.addSpacing(10)

        # ── CONTROLES GLOBAIS ────────────────────────────────────
        self.btn_theme = QPushButton("☀️") # Sol por padrão (toggle para lua)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setFixedSize(36, 36)
        self.btn_theme.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 18px;
                font-size: 16px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.08); }
        """)
        self.btn_theme.clicked.connect(self.theme_toggled.emit)
        self.layout.addWidget(self.btn_theme)

        # Sombra suave inferior
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def update_theme(self, is_dark, colors):
        """Atualiza o estilo do header conforme o tema do sistema"""
        self.btn_theme.setText("🌙" if is_dark else "☀️")
        bg_color = colors['sidebar_bg']
        border_color = colors['border']
        text_color = colors['text_bright']
        
        self.setStyleSheet(f"""
            QFrame#nav_header {{
                background-color: {bg_color};
                border-bottom: 1px solid {border_color};
            }}
            QLabel {{ color: {text_color}; }}
        """)
        
        # Ajusta HUD
        hud_bg = "rgba(0,0,0,0.2)" if is_dark else "rgba(255,255,255,0.1)"
        self.hud_container.setStyleSheet(f"""
            QFrame#hud_nav {{
                background: {hud_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)

    # ── MÉTODOS DE ATUALIZAÇÃO TELEMETRIA ────────────────────────
    def set_arduino_status(self, connected):
        color = "#10B981" if connected else "#EF4444"
        self.arduino_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:10px;")
        self.arduino_indicator.setText(f"● ARDUINO: {'OK' if connected else 'OFF'}")

    def set_fps(self, fps):
        color = "#10B981" if fps > 22 else ("#F59E0B" if fps > 12 else "#EF4444")
        self.fps_indicator.setText(f"● FPS: {int(fps)}")
        self.fps_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:10px;")

    def set_eeg_quality(self, signal):
        # signal 0-200 (baixo é melhor)
        color = "#10B981" if signal < 50 else ("#F59E0B" if signal < 200 else "#EF4444")
        text = "FORTE" if signal < 50 else ("MÉDIO" if signal < 200 else "SEM SINAL")
        self.eeg_indicator.setText(f"● EEG: {text}")
        self.eeg_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:10px;")
