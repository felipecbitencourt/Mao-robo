import sys
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
    QLineEdit, QProgressBar, QSizePolicy, QRadioButton, QButtonGroup,
    QComboBox
)

from core.hub_controller import HubController
from ui.components.video_display import VideoDisplay
from ui.components.gesture_display import GestureDisplay
from ui.components.custom_buttons import ActionButton, AnimatedButton


# ══════════════════════════════════════════════════════════════════
#  Paletas
# ══════════════════════════════════════════════════════════════════
DARK_THEME = {
    "bg":           "#0C0C14",
    "sidebar_bg":   "#0F0F1C",
    "card_bg":      "#161624",
    "border":       "#1E1E34",
    "text":         "#8888AA",
    "text_dim":     "#505068",
    "text_bright":  "#E0E0FF",
    "bar_bg":       "#1E1E34",
    "input_bg":     "#161624",
    "input_color":  "#E0E0FF",
    "toggle_label": "☀  Modo Claro",
    "toggle_style": (
        "background-color:#1E1E34; color:#8888AA; border:1px solid #2A2A44;"
        " border-radius:14px; padding:4px 14px; font-size:11px;"
    ),
}

LIGHT_THEME = {
    "bg":           "#F2F2F8",
    "sidebar_bg":   "#E8E8F4",
    "card_bg":      "#FFFFFF",
    "border":       "#D0D0E4",
    "text":         "#555570",
    "text_dim":     "#9898B0",
    "text_bright":  "#1A1A2E",
    "bar_bg":       "#E0E0EE",
    "input_bg":     "#FFFFFF",
    "input_color":  "#1A1A2E",
    "toggle_label": "🌙  Modo Escuro",
    "toggle_style": (
        "background-color:#FFFFFF; color:#555570; border:1px solid #C8C8DC;"
        " border-radius:14px; padding:4px 14px; font-size:11px;"
    ),
}


# ══════════════════════════════════════════════════════════════════
#  Helpers visuais
# ══════════════════════════════════════════════════════════════════
def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color:#454560; font-size:9px; font-weight:bold;"
        " letter-spacing:2px; padding:14px 0 6px 0;"
    )
    return lbl


def _h_divider(color: str = "#1E1E34") -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"background:{color}; border:none; max-height:1px;")
    return line


def _card_wrap(inner_widget: QWidget, theme: dict) -> QFrame:
    """Envolve um widget em um card com borda arredondada."""
    card = QFrame()
    card.setObjectName("datacard")
    card.setStyleSheet(f"""
        QFrame#datacard {{
            background-color: {theme['card_bg']};
            border: 1px solid {theme['border']};
            border-radius: 14px;
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(inner_widget)
    return card


def _panel_header(title: str, dot_color: str, theme: dict) -> QWidget:
    """Faixa de cabeçalho para um painel/card."""
    bar = QWidget()
    bar.setFixedHeight(36)
    bar.setStyleSheet(f"""
        background-color: {theme['border']};
        border-top-left-radius: 14px;
        border-top-right-radius: 14px;
    """)
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(14, 0, 14, 0)

    dot = QLabel("●")
    dot.setStyleSheet(f"color:{dot_color}; font-size:9px; margin-right:6px;")
    layout.addWidget(dot)

    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        f"color:{theme['text']}; font-size:10px; font-weight:bold; letter-spacing:1.5px;"
    )
    layout.addWidget(lbl)
    layout.addStretch()
    return bar


# ══════════════════════════════════════════════════════════════════
#  Janela principal
# ══════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hub = HubController()
        self.setWindowTitle("Mão Robótica Pro")
        self.resize(1140, 820)
        self._dark_mode = self.hub.config.get("theme_dark_mode", True)

        self.hub.status_signal.connect(self.update_status_bar)
        self.hub.prediction_signal.connect(self.update_prediction)
        self.hub.glove_signal.connect(self.update_glove_data)
        self.hub.eeg_signal.connect(self.update_eeg_data)

        self._init_ui()

    # ── Tema ──────────────────────────────────────────────────── #
    def _current_theme(self):
        return DARK_THEME if self._dark_mode else LIGHT_THEME

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.hub.config.set("theme_dark_mode", self._dark_mode)
        self._apply_theme()

    def _apply_theme(self):
        t = self._current_theme()

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {t['bg']};
                font-family: 'Segoe UI', sans-serif;
            }}
            QLabel {{
                color: {t['text']};
            }}
            QFrame#sidebar {{
                background-color: {t['sidebar_bg']};
                border-right: 1px solid {t['border']};
            }}
            QFrame#central_content {{
                background-color: {t['bg']};
            }}
            QFrame#videopanel {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 14px;
            }}
            QFrame#datapanel {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 14px;
            }}
        """)

        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background-color:{t['input_bg']}; color:{t['input_color']};
                border:1px solid {t['border']}; border-radius:6px; padding:5px 8px; font-size:13px;
            }}
            QComboBox QAbstractItemView {{
                background-color:{t['input_bg']}; color:{t['input_color']};
                selection-background-color:#3B82F6; selection-color:#FFFFFF;
            }}
        """)

        self.status_bar_label.setStyleSheet(f"""
            padding:10px 18px; border-top:1px solid {t['border']};
            color:{t['text_dim']}; font-size:11px; font-family:'Consolas', monospace;
            background-color:{t['sidebar_bg']};
        """)

        for bar in self.glove_bars:
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color:{t['bar_bg']}; border-radius:4px; }}
                QProgressBar::chunk {{ background-color:#10B981; border-radius:4px; }}
            """)

        self.attn_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:{t['bar_bg']}; border-radius:6px;
                color:{t['input_color']}; text-align:center; font-size:10px; }}
            QProgressBar::chunk {{ background-color:#EF4444; border-radius:6px; }}
        """)
        self.med_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:{t['bar_bg']}; border-radius:6px;
                color:{t['input_color']}; text-align:center; font-size:10px; }}
            QProgressBar::chunk {{ background-color:#3B82F6; border-radius:6px; }}
        """)

        self.btn_theme_toggle.setText(t['toggle_label'])
        self.btn_theme_toggle.setStyleSheet(t['toggle_style'])

        self.attn_label.setStyleSheet(f"color:{t['text_dim']}; font-size:11px; font-weight:bold;")
        self.med_label.setStyleSheet(f"color:{t['text_dim']}; font-size:11px; font-weight:bold;")

        current_color = "#10B981" if "#10B981" in self.result_label.styleSheet() else t['text_bright']
        self.result_label.setStyleSheet(
            f"font-size:36px; font-weight:bold; color:{current_color};"
        )

    # ── Calibração ────────────────────────────────────────────── #
    def start_calibration_sequence(self):
        self.btn_calibrate_glove.setEnabled(False)
        self.hub.status_signal.emit("Iniciando calibração em 3 passos...")
        self._run_calib_step("FECHE A MÃO COMPLETAMENTE", "CLOSED", 0)
        QTimer.singleShot(4000, lambda: self._run_calib_step("MANTENHA A MÃO RELAXADA (MEIO)", "HALF", 1))
        QTimer.singleShot(8000, lambda: self._run_calib_step("ABRA A MÃO COMPLETAMENTE", "OPEN", 2))
        QTimer.singleShot(12000, self.finish_calibration_ui)

    def _run_calib_step(self, msg, state, step_idx):
        print(f"DEBUG UI: Passo {step_idx} - {state}")
        self.result_label.setText(msg)
        self.result_label.setStyleSheet("font-size:22px; color:#F59E0B; font-weight:bold;")
        QTimer.singleShot(1000, lambda: self.hub.start_glove_calibration(state))
        QTimer.singleShot(4000, lambda: self.hub.finish_glove_calibration_step())

    def finish_calibration_ui(self):
        self.btn_calibrate_glove.setEnabled(True)
        self.result_label.setText("CALIBRAÇÃO CONCLUÍDA")
        self.result_label.setStyleSheet("font-size:30px; color:#10B981; font-weight:bold;")
        self.hub.status_signal.emit("Luva calibrada com sucesso!")
        t = self._current_theme()
        QTimer.singleShot(2000, lambda: self.result_label.setStyleSheet(
            f"font-size:36px; color:{t['text_bright']}; font-weight:bold;"
        ))

    def closeEvent(self, event):
        print("Fechando aplicação... parando threads.")
        self.hub.stop()
        event.accept()

    # ── Construção da UI ──────────────────────────────────────── #
    def _init_ui(self):
        t = self._current_theme()

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color:{t['bg']}; font-family:'Segoe UI', sans-serif; }}
            QLabel {{ color:{t['text']}; }}
            QFrame#sidebar {{ background-color:{t['sidebar_bg']}; border-right:1px solid {t['border']}; }}
            QFrame#central_content {{ background-color:{t['bg']}; }}
            QFrame#videopanel {{
                background-color:{t['card_bg']}; border:1px solid {t['border']}; border-radius:14px;
            }}
            QFrame#datapanel {{
                background-color:{t['card_bg']}; border:1px solid {t['border']}; border-radius:14px;
            }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(268)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 28, 20, 24)
        sidebar_layout.setSpacing(0)

        # Bloco de branding
        brand_widget = QWidget()
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        accent_bar = QFrame()
        accent_bar.setFixedSize(32, 3)
        accent_bar.setStyleSheet("background-color:#E94560; border-radius:2px;")
        brand_layout.addWidget(accent_bar)
        brand_layout.addSpacing(8)

        title_lbl = QLabel("MÃO ROBÓTICA")
        title_lbl.setStyleSheet(
            "font-size:18px; font-weight:bold; color:#E0E0FF; letter-spacing:1px;"
        )
        brand_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel("PRO HUB  ·  MULTIMODAL")
        subtitle_lbl.setStyleSheet("font-size:10px; color:#505068; letter-spacing:2px;")
        brand_layout.addWidget(subtitle_lbl)

        sidebar_layout.addWidget(brand_widget)
        sidebar_layout.addSpacing(4)
        sidebar_layout.addWidget(_h_divider("#1E1E34"))

        # Seção Inputs
        sidebar_layout.addWidget(_section_label("Inputs Disponíveis"))

        self.btn_cam = AnimatedButton("🎥  CÂMERA", accent_color="#3B82F6")
        self.btn_cam.setCheckable(True)
        self.btn_cam.toggled.connect(self._toggle_camera)
        sidebar_layout.addWidget(self.btn_cam)
        sidebar_layout.addSpacing(6)

        self.btn_glove = AnimatedButton("🧤  LUVA 5DT", accent_color="#10B981")
        self.btn_glove.setCheckable(True)
        self.btn_glove.toggled.connect(self._toggle_glove)
        sidebar_layout.addWidget(self.btn_glove)
        sidebar_layout.addSpacing(6)

        self.btn_eeg = AnimatedButton("🧠  EEG BRAINLINK", accent_color="#F59E0B")
        self.btn_eeg.setCheckable(True)
        self.btn_eeg.toggled.connect(self._toggle_eeg)
        sidebar_layout.addWidget(self.btn_eeg)

        sidebar_layout.addSpacing(4)
        sidebar_layout.addWidget(_h_divider("#1E1E34"))

        # Seção Saída
        sidebar_layout.addWidget(_section_label("Controle de Saída"))

        port_row = QHBoxLayout()
        port_lbl = QLabel("Porta:")
        port_lbl.setStyleSheet("color:#505068; font-size:12px; font-weight:bold;")
        port_row.addWidget(port_lbl)
        self.port_combo = QComboBox()
        self.port_combo.setFixedHeight(32)
        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background-color:{t['input_bg']}; color:{t['input_color']};
                border:1px solid {t['border']}; border-radius:6px; padding:5px 8px; font-size:13px;
            }}
            QComboBox QAbstractItemView {{
                background-color:{t['input_bg']}; color:{t['input_color']};
                selection-background-color:#3B82F6; selection-color:#FFFFFF;
            }}
        """)
        
        self._refresh_ports_combo()
        self.port_combo.currentTextChanged.connect(self._update_port)
        
        port_row.addWidget(self.port_combo)
        sidebar_layout.addLayout(port_row)
        sidebar_layout.addSpacing(8)

        self.btn_output_hand = AnimatedButton("🦾  MÃO ROBÓTICA: OFF", accent_color="#EF4444")
        self.btn_output_hand.setCheckable(True)
        self.btn_output_hand.toggled.connect(self._toggle_output_hand)
        sidebar_layout.addWidget(self.btn_output_hand)
        sidebar_layout.addSpacing(6)

        self.btn_test_hand = AnimatedButton("⚙️  TESTAR SERVOS", accent_color="#3B82F6")
        self.btn_test_hand.clicked.connect(self.hub.test_arduino_hand)
        sidebar_layout.addWidget(self.btn_test_hand)
        sidebar_layout.addSpacing(6)

        self.btn_auto_ports = AnimatedButton("🔍  DETECTAR PORTAS", accent_color="#8B5CF6")
        self.btn_auto_ports.clicked.connect(self._on_auto_detect_clicked)
        sidebar_layout.addWidget(self.btn_auto_ports)

        sidebar_layout.addStretch()

        # Rodapé da sidebar
        sidebar_footer = QLabel("Sistema v2.0  •  Multimodal")
        sidebar_footer.setStyleSheet("color:#303048; font-size:10px; letter-spacing:1px;")
        sidebar_footer.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(sidebar_footer)

        # ── ÁREA CENTRAL ─────────────────────────────────────────
        self.central_content = QFrame()
        self.central_content.setObjectName("central_content")
        central_layout = QVBoxLayout(self.central_content)
        central_layout.setContentsMargins(28, 22, 28, 0)
        central_layout.setSpacing(18)

        # Header da área central
        header_layout = QHBoxLayout()

        app_title = QLabel("PAINEL DE CONTROLE")
        app_title.setStyleSheet(
            "color:#303048; font-size:11px; font-weight:bold; letter-spacing:2px;"
        )
        header_layout.addWidget(app_title)
        header_layout.addStretch()

        self.btn_theme_toggle = QPushButton(t['toggle_label'])
        self.btn_theme_toggle.setFixedHeight(28)
        self.btn_theme_toggle.setStyleSheet(t['toggle_style'])
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        central_layout.addLayout(header_layout)

        # ── PAINEL DE VÍDEO ──────────────────────────────────────
        self.video_container = QFrame()
        self.video_container.setObjectName("videopanel")
        self.video_container.setMinimumHeight(340)
        video_outer = QVBoxLayout(self.video_container)
        video_outer.setContentsMargins(0, 0, 0, 0)
        video_outer.setSpacing(0)

        video_header = _panel_header("Visão Computacional", "#3B82F6", t)
        video_outer.addWidget(video_header)

        self.video_display = VideoDisplay()
        self.hub.frame_signal.connect(self.video_display.update_frame)
        video_outer.addWidget(self.video_display)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.video_container.setGraphicsEffect(shadow)

        central_layout.addWidget(self.video_container)

        # ── PAINEL DE DADOS ───────────────────────────────────────
        self.data_panel = QFrame()
        self.data_panel.setObjectName("datapanel")
        data_outer = QVBoxLayout(self.data_panel)
        data_outer.setContentsMargins(0, 0, 0, 0)
        data_outer.setSpacing(0)

        data_header = _panel_header("Dados em Tempo Real", "#10B981", t)
        data_outer.addWidget(data_header)

        data_inner = QWidget()
        data_inner_layout = QHBoxLayout(data_inner)
        data_inner_layout.setContentsMargins(16, 14, 16, 14)
        data_inner_layout.setSpacing(20)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.gesture_display = GestureDisplay(
            images_path=os.path.join(base_dir, "luva", "gesture-images")
        )
        data_inner_layout.addWidget(self.gesture_display)

        # Coluna de texto e métricas
        text_col = QVBoxLayout()
        text_col.setSpacing(8)

        self.result_label = QLabel("AGUARDANDO GESTO")
        self.result_label.setStyleSheet(
            f"font-size:36px; font-weight:bold; color:{t['text_bright']};"
        )
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_col.addWidget(self.result_label)

        self.source_label = QLabel("Fonte: —")
        self.source_label.setStyleSheet(
            "color:#E94560; font-weight:bold; font-size:12px; letter-spacing:1px;"
        )
        text_col.addWidget(self.source_label)

        text_col.addSpacing(4)

        # Telemetria da Luva
        self.glove_telemetry = QFrame()
        glove_tel_layout = QVBoxLayout(self.glove_telemetry)
        glove_tel_layout.setContentsMargins(0, 4, 0, 4)
        glove_tel_layout.setSpacing(5)

        finger_names = ["Polegar", "Indicador", "Médio", "Anelar", "Mínimo"]
        self.glove_bars = []
        for i, fname in enumerate(finger_names):
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(fname)
            lbl.setFixedWidth(68)
            lbl.setStyleSheet(f"color:{t['text_dim']}; font-size:10px;")
            bar = QProgressBar()
            bar.setFixedHeight(7)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color:{t['bar_bg']}; border-radius:4px; }}
                QProgressBar::chunk {{ background-color:#10B981; border-radius:4px; }}
            """)
            row.addWidget(lbl)
            row.addWidget(bar)
            glove_tel_layout.addLayout(row)
            self.glove_bars.append(bar)

        self.glove_telemetry.hide()
        text_col.addWidget(self.glove_telemetry)

        self.btn_calibrate_glove = QPushButton("CALIBRAR LUVA")
        self.btn_calibrate_glove.setFixedHeight(32)
        self.btn_calibrate_glove.setCursor(Qt.PointingHandCursor)
        self.btn_calibrate_glove.setStyleSheet("""
            QPushButton {
                background-color:#3B82F618; color:#3B82F6;
                border:1px solid #3B82F660; border-bottom:2px solid #3B82F6;
                border-radius:7px; font-weight:bold; font-size:12px; letter-spacing:1px;
            }
            QPushButton:hover { background-color:#3B82F630; color:#FFFFFF; }
            QPushButton:disabled { color:#303048; border-color:#252540; background:transparent; }
        """)
        self.btn_calibrate_glove.clicked.connect(self.start_calibration_sequence)
        text_col.addWidget(self.btn_calibrate_glove)

        # Telemetria EEG
        self.eeg_telemetry = QFrame()
        eeg_tel_layout = QVBoxLayout(self.eeg_telemetry)
        eeg_tel_layout.setSpacing(6)
        eeg_tel_layout.setContentsMargins(0, 4, 0, 4)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)
        mode_lbl = QLabel("CONTROLE:")
        mode_lbl.setStyleSheet(f"color:{t['text_dim']}; font-size:10px; font-weight:bold;")
        mode_layout.addWidget(mode_lbl)
        
        self.mode_group = QButtonGroup(self.eeg_telemetry)
        self.rb_none = QRadioButton("Mudo")
        self.rb_attn = QRadioButton("Atenção")
        self.rb_med = QRadioButton("Meditação")
        
        for rb in [self.rb_none, self.rb_attn, self.rb_med]:
            rb.setStyleSheet(f"color:{t['text_bright']}; font-size:10px;")
            self.mode_group.addButton(rb)
            mode_layout.addWidget(rb)
            
        mode_layout.addStretch()
        self.rb_none.setChecked(True)
        self.rb_none.toggled.connect(lambda c: self._set_eeg_mode('none') if c else None)
        self.rb_attn.toggled.connect(lambda c: self._set_eeg_mode('attention') if c else None)
        self.rb_med.toggled.connect(lambda c: self._set_eeg_mode('meditation') if c else None)
        eeg_tel_layout.addLayout(mode_layout)

        attn_row = QHBoxLayout()
        attn_row.setSpacing(10)
        self.attn_label = QLabel("ATENÇÃO")
        self.attn_label.setFixedWidth(80)
        self.attn_label.setStyleSheet(f"color:{t['text_dim']}; font-size:11px; font-weight:bold;")
        self.attn_bar = QProgressBar()
        self.attn_bar.setFixedHeight(12)
        self.attn_bar.setRange(0, 100)
        self.attn_bar.setTextVisible(True)
        self.attn_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:{t['bar_bg']}; border-radius:6px;
                color:{t['input_color']}; text-align:center; font-size:10px; }}
            QProgressBar::chunk {{ background-color:#EF4444; border-radius:6px; }}
        """)
        attn_row.addWidget(self.attn_label)
        attn_row.addWidget(self.attn_bar)
        eeg_tel_layout.addLayout(attn_row)

        med_row = QHBoxLayout()
        med_row.setSpacing(10)
        self.med_label = QLabel("MEDITAÇÃO")
        self.med_label.setFixedWidth(80)
        self.med_label.setStyleSheet(f"color:{t['text_dim']}; font-size:11px; font-weight:bold;")
        self.med_bar = QProgressBar()
        self.med_bar.setFixedHeight(12)
        self.med_bar.setRange(0, 100)
        self.med_bar.setTextVisible(True)
        self.med_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:{t['bar_bg']}; border-radius:6px;
                color:{t['input_color']}; text-align:center; font-size:10px; }}
            QProgressBar::chunk {{ background-color:#3B82F6; border-radius:6px; }}
        """)
        med_row.addWidget(self.med_label)
        med_row.addWidget(self.med_bar)
        eeg_tel_layout.addLayout(med_row)

        self.eeg_label = QLabel("SINAL: —")
        self.eeg_label.setStyleSheet(
            "color:#F59E0B; font-family:'Consolas', monospace; font-size:11px;"
        )
        eeg_tel_layout.addWidget(self.eeg_label)

        self.eeg_telemetry.hide()
        text_col.addWidget(self.eeg_telemetry)

        text_col.addStretch()
        data_inner_layout.addLayout(text_col)
        data_outer.addWidget(data_inner)
        central_layout.addWidget(self.data_panel)

        # ── BOTÕES DE AÇÃO ────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(16)

        self.btn_start = ActionButton("▶  INICIAR MOTOR", color="#10B981")
        self.btn_start.clicked.connect(self.hub.start)

        self.btn_stop = ActionButton("■  PARAR TUDO", color="#EF4444")
        self.btn_stop.clicked.connect(self.hub.stop)

        self.btn_calibrate = ActionButton("◈  CALIBRAR", color="#3B82F6")
        self.btn_calibrate.clicked.connect(self.hub.calibrate)

        action_row.addWidget(self.btn_start)
        action_row.addWidget(self.btn_stop)
        action_row.addWidget(self.btn_calibrate)
        central_layout.addLayout(action_row)

        # ── BARRA DE STATUS ───────────────────────────────────────
        self.status_bar_label = QLabel("● SISTEMA PRONTO")
        self.status_bar_label.setStyleSheet(f"""
            padding:10px 18px; border-top:1px solid {t['border']};
            color:{t['text_dim']}; font-size:11px; font-family:'Consolas', monospace;
            background-color:{t['sidebar_bg']};
        """)
        central_layout.addWidget(self.status_bar_label)

        central_layout.setContentsMargins(28, 22, 28, 0)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.central_content)

    # ── Callbacks ─────────────────────────────────────────────── #
    def _refresh_ports_combo(self):
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        
        from outputs.arduino_output import ArduinoOutput
        ports = ArduinoOutput.list_available_ports()
        
        saved_port = self.hub.config.get("arduino_port", "COM5")
        idx_to_select = -1
        
        for i, port_info in enumerate(ports):
            port_name = port_info.split(' ')[0]
            self.port_combo.addItem(port_info, port_name)
            if port_name == saved_port:
                idx_to_select = i
                
        if not ports:
            self.port_combo.addItem(f"{saved_port} (Desconectado)", saved_port)
            idx_to_select = 0

        if idx_to_select >= 0:
            self.port_combo.setCurrentIndex(idx_to_select)
            
        self.port_combo.blockSignals(False)
        if self.port_combo.currentData():
            self.hub.arduino.port = self.port_combo.currentData()

    def _on_auto_detect_clicked(self):
        self.hub.auto_detect_all_ports()
        self._refresh_ports_combo()

    def _update_port(self, text):
        real_port = self.port_combo.currentData()
        if not real_port: real_port = text.split(' ')[0]
        
        if self.hub.arduino:
            self.hub.arduino.port = real_port
            self.hub.config.set("arduino_port", real_port)

    def _toggle_output_hand(self, checked):
        if checked:
            self.btn_output_hand.setText("🦾  MÃO ROBÓTICA: ON")
            self.btn_output_hand._accent_color = "#10B981"
            self.btn_output_hand._update_style(checked=True)
            self.hub.set_hand_output(True)
        else:
            self.btn_output_hand.setText("🦾  MÃO ROBÓTICA: OFF")
            self.btn_output_hand._accent_color = "#EF4444"
            self.btn_output_hand._update_style(checked=False)
            self.hub.set_hand_output(False)

    def _toggle_camera(self, checked):
        self.btn_cam._update_style(checked)
        self.hub.set_camera_active(checked)

    def _toggle_glove(self, checked):
        self.btn_glove._update_style(checked)
        self.hub.set_glove_active(checked)

    def _toggle_eeg(self, checked):
        self.btn_eeg._update_style(checked)
        self.hub.set_eeg_active(checked)

    def _set_eeg_mode(self, mode):
        self.hub.eeg_control_mode = mode

    def update_status_bar(self, message):
        self.status_bar_label.setText(f"● {message.upper()}")

    def update_glove_data(self, data):
        self.glove_telemetry.show()
        t = self._current_theme()
        sensors = data.get("sensors", [])
        for i, val in enumerate(sensors[:5]):
            if i < len(self.glove_bars):
                self.glove_bars[i].setValue(int(val * 100))
                color = "#10B981" if val < 0.5 else "#F59E0B"
                self.glove_bars[i].setStyleSheet(f"""
                    QProgressBar {{ background-color:{t['bar_bg']}; border-radius:4px; }}
                    QProgressBar::chunk {{ background-color:{color}; border-radius:4px; }}
                """)

    def update_prediction(self, data):
        t = self._current_theme()
        gid    = data.get("gesture_id", -1)
        pred   = data.get("prediction", "N/A")
        conf   = data.get("confidence", 0)
        source = data.get("source", "UNKNOWN")

        print(f"*** UI RECEIVE: {pred} FROM {source} ***")

        self.result_label.setText(pred)
        self.source_label.setText(f"FONTE: {source}  ·  {conf}%")
        self.gesture_display.update_gesture(gid)

        color = "#10B981" if conf > 85 else t['text_bright']
        self.result_label.setStyleSheet(f"font-size:36px; font-weight:bold; color:{color};")

    def update_eeg_data(self, data):
        self.eeg_telemetry.show()
        att = data.get("attention", 0)
        med = data.get("meditation", 0)
        sig = data.get("signal", 200)

        self.attn_bar.setValue(att)
        self.med_bar.setValue(med)

        status_text = "BOM" if sig < 50 else ("FALHANDO" if sig < 200 else "SEM SINAL")
        self.eeg_label.setText(f"SINAL: {sig:3d}  [{status_text}]")

        color = "#10B981" if sig < 50 else "#EF4444"
        self.eeg_label.setStyleSheet(
            f"color:{color}; font-family:'Consolas', monospace; font-size:11px;"
        )


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
