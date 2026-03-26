import sys
import os
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTextCursor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
    QLineEdit, QProgressBar, QSizePolicy, QRadioButton, QButtonGroup,
    QComboBox, QStackedWidget, QDoubleSpinBox, QTextEdit, QGridLayout
)

from core.hub_controller import HubController
from ui.components.video_display import VideoDisplay
from ui.components.gesture_display import GestureDisplay
from ui.components.custom_buttons import ActionButton, AnimatedButton
from ui.components.spectrogram_widget import SpectrogramWidget


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Paletas
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
DARK_THEME = {
    "bg":           "#0E0E14",
    "sidebar_bg":   "#14141E",
    "card_bg":      "#1A1A26",
    "border":       "#2B2B3E",
    "text":         "#A7A7C6",
    "text_dim":     "#7D7D9C",
    "text_bright":  "#F4F4FD",
    "bar_bg":       "#2B2B3E",
    "input_bg":     "#1A1A26",
    "input_color":  "#F4F4FD",
    "toggle_label": "â˜€ï¸  Modo Claro",
    "toggle_style": (
        "background-color:#2B2B3E; color:#A7A7C6; border:1px solid #3A3A52;"
        " border-radius:14px; padding:4px 14px; font-size:11px; font-weight:bold;"
    ),
}

LIGHT_THEME = {
    "bg":           "#F6F6FA",
    "sidebar_bg":   "#FFFFFF",
    "card_bg":      "#FFFFFF",
    "border":       "#D8D8E5",
    "text":         "#3F3F56",
    "text_dim":     "#686885",
    "text_bright":  "#0A0A10",
    "bar_bg":       "#EBECF2",
    "input_bg":     "#FBFBFC",
    "input_color":  "#0A0A10",
    "toggle_label": "ðŸŒ™  Modo Escuro",
    "toggle_style": (
        "background-color:#FFFFFF; color:#3F3F56; border:1px solid #C8C8DC;"
        " border-radius:14px; padding:4px 14px; font-size:11px; font-weight:bold;"
    ),
}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Helpers visuais
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("section_lbl")
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
    """Faixa de cabeÃ§alho para um painel/card."""
    bar = QWidget()
    bar.setFixedHeight(36)
    bar.setObjectName("panel_header")
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(14, 0, 14, 0)

    dot = QLabel("â—")
    dot.setStyleSheet(f"color:{dot_color}; font-size:9px; margin-right:6px;")
    layout.addWidget(dot)

    lbl = QLabel(title.upper())
    lbl.setObjectName("panel_title")
    layout.addWidget(lbl)
    layout.addStretch()
    return bar

from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt

class WavePlotWidget(QWidget):
    def __init__(self, color_str, parent=None):
        super().__init__(parent)
        self.color = QColor(color_str)
        self.history = [0] * 300
        self.bg_col = QColor("#1A1A26")
        self.grid_col = QColor("#2B2B3E")
        self.setMinimumHeight(120)
    
    def update_theme(self, bg_str, grid_str):
        self.bg_col = QColor(bg_str)
        self.grid_col = QColor(grid_str)
        self.update()
        
    def add_value(self, val):
        self.history.pop(0)
        self.history.append(val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_col)
        
        painter.setPen(QPen(self.grid_col, 1, Qt.DashLine))
        painter.drawLine(0, self.height() // 2, self.width(), self.height() // 2)
        
        pen = QPen(self.color, 2)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        if w == 0 or h == 0: return
        dx = w / max(1, len(self.history) - 1)
        for i in range(len(self.history) - 1):
            x1 = int(i * dx)
            y1 = int(h - (self.history[i] / 100.0) * h)
            x2 = int((i + 1) * dx)
            y2 = int(h - (self.history[i+1] / 100.0) * h)
            painter.drawLine(x1, y1, x2, y2)

class StreamRedirector(QObject):
    text_written = Signal(str)

    def __init__(self, stream):
        super().__init__()
        self.stream = stream

    def write(self, text):
        self.text_written.emit(str(text))
        self.stream.write(text)

    def flush(self):
        self.stream.flush()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Janela principal
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hub = HubController()
        self.setWindowTitle("MÃ£o RobÃ³tica Pro")
        self.resize(1140, 820)
        self._dark_mode = self.hub.config.get("theme_dark_mode", True)

        self.hub.status_signal.connect(self.update_status_bar)
        self.hub.prediction_signal.connect(self.update_prediction)
        self.hub.glove_signal.connect(self.update_glove_data)
        self.hub.eeg_signal.connect(self.update_eeg_data)
        self.hub.discovery_finished_signal.connect(self._on_discovery_finished)

        # GamificaÃ§Ã£o EEG (Desafio de 60s)
        self.eeg_test_active = False
        self.eeg_test_phase = 0
        self.eeg_test_seconds = 0
        self.max_focus = 0
        self.max_meditation = 0
        self.eeg_timer = QTimer(self)
        self.eeg_timer.timeout.connect(self._eeg_test_tick)

        # CalibraÃ§Ã£o ClÃ­nica (10 ciclos)
        self.clin_cal_active = False
        self.clin_cal_cycle = 0
        self.clin_cal_phase = 0 # 0: Aguardando, 1: OPEN, 2: CLOSED
        self.clin_cal_seconds = 0
        self.clin_timer = QTimer(self)
        self.clin_timer.timeout.connect(self._clin_cal_tick)

        self._init_ui()

        # Redirecionamento de Logs para In-App Console
        self.stdout_redirector = StreamRedirector(sys.stdout)
        self.stderr_redirector = StreamRedirector(sys.stderr)
        self.stdout_redirector.text_written.connect(self.append_log)
        self.stderr_redirector.text_written.connect(self.append_log)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector

    def append_log(self, text):
        if hasattr(self, 'log_terminal'):
            self.log_terminal.moveCursor(QTextCursor.End)
            self.log_terminal.insertPlainText(text)
            self.log_terminal.moveCursor(QTextCursor.End)

    # â”€â”€ Tema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ #
    def _current_theme(self):
        return DARK_THEME if self._dark_mode else LIGHT_THEME

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.hub.config.set("theme_dark_mode", self._dark_mode)
        self._apply_theme()

    def _switch_tab(self, idx):
        self.stacked_widget.setCurrentIndex(idx)
        self._apply_theme()

    def _apply_theme(self):
        t = self._current_theme()

        if hasattr(self, 'btn_nav_dash'):
            self.nav_container.setStyleSheet(f"background-color:{t['input_bg']}; border-radius:10px;")
            nav_style = f"""
                QPushButton {{
                    background-color:transparent; color:{t['text_dim']}; 
                    border:none; border-radius:8px; padding:12px 0px; 
                    font-weight:bold; font-size:13px; letter-spacing:1px;
                }}
                QPushButton:hover {{ color:{t['text_bright']}; background-color:rgba(255,255,255,0.03); }}
            """
            nav_active = f"""
                QPushButton {{
                    background-color:{t['card_bg']}; color:{t['text_bright']}; 
                    border:1px solid {t['border']}; border-radius:8px; 
                    padding:12px 0px; font-weight:bold; font-size:13px; letter-spacing:1px;
                }}
            """
            idx = self.stacked_widget.currentIndex()
            self.btn_nav_dash.setStyleSheet(nav_active if idx == 0 else nav_style)
            self.btn_nav_settings.setStyleSheet(nav_active if idx == 1 else nav_style)

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color:{t['bg']}; font-family:'Segoe UI', sans-serif; }}
            QLabel {{ color:{t['text']}; background:transparent; }}
            QLabel#title_lbl {{ font-size:18px; font-weight:bold; color:{t['text_bright']}; letter-spacing:1px; }}
            QLabel#subtitle_lbl {{ font-size:10px; color:{t['text_dim']}; letter-spacing:2px; text-transform:uppercase; }}
            QLabel#sidebar_footer {{ color:{t['text_dim']}; font-size:10px; letter-spacing:1px; }}
            QLabel#app_title {{ color:{t['text_bright']}; font-size:14px; font-weight:bold; letter-spacing:2px; }}
            QLabel#section_lbl {{ color:{t['text_dim']}; font-size:10px; font-weight:bold; letter-spacing:1.5px; padding:12px 0 4px 0; }}
            QLabel#dim_label {{ color:{t['text_dim']}; font-size:10px; font-weight:bold; letter-spacing:0.5px; }}
            QLabel#glove_lbl {{ color:{t['text']}; font-size:11px; font-weight:500; }}
            QLabel#panel_title {{ color:{t['text']}; font-size:11px; font-weight:bold; letter-spacing:1.5px; }}
            QWidget#panel_header {{ background-color:{t['border']}; border-top-left-radius:14px; border-top-right-radius:14px; border-bottom:1px solid {t['border']}; }}
            QLabel#status_bar {{ padding:10px 18px; border-top:1px solid {t['border']}; color:{t['text_dim']}; font-size:11px; font-family:'Consolas', monospace; background-color:{t['sidebar_bg']}; }}
            QRadioButton {{ color:{t['text_bright']}; font-size:11px; font-weight:500; background:transparent; padding:2px; }}
            QFrame#sidebar {{ background-color:{t['sidebar_bg']}; border-right:1px solid {t['border']}; }}
            QFrame#central_content {{ background-color:{t['bg']}; }}
            QFrame#videopanel, QFrame#datapanel {{
                background-color:{t['card_bg']}; border:1px solid {t['border']}; border-radius:14px;
            }}
            QLabel#lbl_idle {{ color:{t['text_dim']}; font-size:16px; font-weight:bold; letter-spacing:1px; }}
            QProgressBar {{ background-color:{t['bar_bg']}; border-radius:12px; }}
            QProgressBar::chunk {{ background-color:#10B981; border-radius:12px; }}
            QProgressBar#attn_bar::chunk {{ background-color:#EF4444; }}
            QProgressBar#med_bar::chunk {{ background-color:#3B82F6; }}
            QProgressBar#attn_bar, QProgressBar#med_bar {{ color:{t['input_color']}; text-align:center; font-size:14px; font-weight:bold; }}

            QDoubleSpinBox {{
                background-color:{t['input_bg']}; color:{t['text_bright']}; 
                border:1px solid {t['border']}; border-radius:6px; 
                padding:4px; font-weight:bold; font-size:12px; font-family:'Consolas', monospace;
            }}
            QDoubleSpinBox:focus {{ border:1px solid #10B981; }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width:14px; border:none; background:transparent; }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background:{t['border']}; border-radius:4px; }}
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

        self.btn_theme_toggle.setText(t['toggle_label'])
        self.btn_theme_toggle.setStyleSheet(t['toggle_style'])

        if hasattr(self, 'attn_plot'):
            self.attn_plot.update_theme(t['input_bg'], t['border'])
            self.med_plot.update_theme(t['input_bg'], t['border'])
        
        if hasattr(self, 'custom_plots'):
            for plot in self.custom_plots.values():
                plot.update_theme(t['input_bg'], t['border'])

        current_color = "#10B981" if "#10B981" in self.result_label.styleSheet() else t['text_bright']
        self.result_label.setStyleSheet(
            f"font-size:36px; font-weight:bold; color:{current_color};"
        )

    # â”€â”€ CalibraÃ§Ã£o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ #
    # â”€â”€ CalibraÃ§Ã£o ClÃ­nica (10 Ciclos) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ #
    def start_calibration_sequence(self):
        """Inicia o protocolo clÃ­nico de 10 ciclos"""
        self.btn_calibrate_glove.setEnabled(False)
        self.clin_cal_active = True
        self.clin_cal_cycle = 1
        self.clin_cal_phase = 1 # Inicia com OPEN
        self.clin_cal_seconds = 5
        
        self.hub.status_signal.emit("Iniciando Protocolo ClÃ­nico (10 Ciclos)...")
        self._update_clin_cal_ui()
        self.clin_timer.start(1000)

    def _clin_cal_tick(self):
        if not self.clin_cal_active:
            return

        self.clin_cal_seconds -= 1
        
        # Notifica o Hub para comeÃ§ar/continuar capturando no estÃ¡gio atual
        if self.clin_cal_seconds == 4: # No primeiro segundo do tick (5->4), garante que o hub estÃ¡ pronto
            stage = 'OPEN' if self.clin_cal_phase == 1 else 'CLOSED'
            self.hub.start_clinical_step(stage)

        if self.clin_cal_seconds <= 0:
            # Finaliza o estÃ¡gio atual no Hub
            self.hub.stop_clinical_step()
            
            if self.clin_cal_phase == 1:
                # Muda para fase CLOSED
                self.clin_cal_phase = 2
                self.clin_cal_seconds = 5
            else:
                # Ciclo completo, verifica se acabou
                if self.clin_cal_cycle >= 10:
                    self.finish_calibration_ui()
                    return
                else:
                    self.clin_cal_cycle += 1
                    self.clin_cal_phase = 1
                    self.clin_cal_seconds = 5
        
        self._update_clin_cal_ui()

    def _update_clin_cal_ui(self):
        msg = "ABRA A MÃƒO COMPLETAMENTE" if self.clin_cal_phase == 1 else "FECHE A MÃƒO COMPLETAMENTE"
        color = "#10B981" if self.clin_cal_phase == 1 else "#EF4444"
        
        self.result_label.setText(f"C{self.clin_cal_cycle}/10: {msg} ({self.clin_cal_seconds}s)")
        self.result_label.setStyleSheet(f"font-size:20px; color:{color}; font-weight:bold;")

    def finish_calibration_ui(self):
        self.clin_cal_active = False
        self.clin_timer.stop()
        
        success = self.hub.calculate_clinical_final()
        
        self.btn_calibrate_glove.setEnabled(True)
        if success:
            self.result_label.setText("CALIBRAÃ‡ÃƒO CLÃNICA CONCLUÃDA")
            self.result_label.setStyleSheet("font-size:28px; color:#10B981; font-weight:bold;")
            self.hub.status_signal.emit("Protocolo finalizado com sucesso!")
        else:
            self.result_label.setText("ERRO NA CALIBRAÃ‡ÃƒO")
            self.result_label.setStyleSheet("font-size:28px; color:#EF4444; font-weight:bold;")

        t = self._current_theme()
        QTimer.singleShot(3000, lambda: self.result_label.setStyleSheet(
            f"font-size:36px; color:{t['text_bright']}; font-weight:bold;"
        ))

    def closeEvent(self, event):
        print("Fechando aplicaÃ§Ã£o... parando threads.")
        self.hub.stop()
        event.accept()

    # â”€â”€ ConstruÃ§Ã£o da UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ #
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

        # â”€â”€ SIDEBAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â”€â”€ SIDEBAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(268)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 28, 12, 24)
        sidebar_layout.setSpacing(0)
        
        # BotÃ£o de colapsar no topo
        self.btn_toggle_sidebar = QPushButton(" â˜° ")
        self.btn_toggle_sidebar.setCheckable(True)
        self.btn_toggle_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setFixedSize(48, 40)
        self.btn_toggle_sidebar.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {t['text_dim']};
                border: 1px solid {t['border']}; border-radius: 8px;
                font-size: 18px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.05); color: {t['text_bright']}; }}
        """)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        toggle_row = QHBoxLayout()
        toggle_row.addWidget(self.btn_toggle_sidebar, 0, Qt.AlignCenter)
        sidebar_layout.addLayout(toggle_row)
        sidebar_layout.addSpacing(16)

        # Bloco de branding
        self.brand_widget = QWidget()
        brand_layout = QVBoxLayout(self.brand_widget)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        accent_bar = QFrame()
        accent_bar.setFixedSize(32, 3)
        accent_bar.setStyleSheet("background-color:#E94560; border-radius:2px;")
        brand_layout.addWidget(accent_bar)
        brand_layout.addSpacing(8)

        self.title_lbl = QLabel("MÃƒO ROBÃ“TICA")
        self.title_lbl.setObjectName("title_lbl")
        brand_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel("PRO HUB  Â·  MULTIMODAL")
        self.subtitle_lbl.setObjectName("subtitle_lbl")
        brand_layout.addWidget(self.subtitle_lbl)

        sidebar_layout.addWidget(self.brand_widget)
        sidebar_layout.addSpacing(24)

        # NavegaÃ§Ã£o via Abas Segmentadas
        self.nav_container = QFrame()
        nav_layout = QHBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(4)
        
        self.btn_nav_dash = QPushButton("ðŸ“Š Dashboard")
        self.btn_nav_settings = QPushButton("âš™ï¸ Specs")
        self.btn_nav_dash.setCursor(Qt.PointingHandCursor)
        self.btn_nav_settings.setCursor(Qt.PointingHandCursor)
        self.btn_nav_dash.clicked.connect(lambda: self._switch_tab(0))
        self.btn_nav_settings.clicked.connect(lambda: self._switch_tab(1))
        
        nav_layout.addWidget(self.btn_nav_dash)
        nav_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addWidget(self.nav_container)
        sidebar_layout.addSpacing(16)
        
        self.lbl_inputs = _section_label("Inputs DisponÃ­veis")
        sidebar_layout.addWidget(self.lbl_inputs)

        self.btn_cam = AnimatedButton("ðŸŽ¥  CÃ‚MERA", accent_color="#3B82F6")
        self.btn_cam.setCheckable(True)
        self.btn_cam.toggled.connect(self._toggle_camera)
        sidebar_layout.addWidget(self.btn_cam)
        sidebar_layout.addSpacing(6)

        self.btn_glove = AnimatedButton("ðŸ§¤  LUVA 5DT", accent_color="#10B981")
        self.btn_glove.setCheckable(True)
        self.btn_glove.toggled.connect(self._toggle_glove)
        sidebar_layout.addWidget(self.btn_glove)
        sidebar_layout.addSpacing(6)

        self.btn_eeg = AnimatedButton("ðŸ§   EEG BRAINLINK", accent_color="#F59E0B")
        self.btn_eeg.setCheckable(True)
        self.btn_eeg.toggled.connect(self._toggle_eeg)
        sidebar_layout.addWidget(self.btn_eeg)

        sidebar_layout.addSpacing(6)
        self.btn_manual = AnimatedButton("ðŸŽ®  CONTROLE MANUAL", accent_color="#8B5CF6")
        self.btn_manual.setCheckable(True)
        self.btn_manual.toggled.connect(self._toggle_manual)
        sidebar_layout.addWidget(self.btn_manual)
        
        sidebar_layout.addSpacing(18)
        self.lbl_outputs = _section_label("Outputs Habilitados")
        sidebar_layout.addWidget(self.lbl_outputs)

        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        sidebar_layout.addSpacing(6)

        self.btn_output_csv = AnimatedButton("ðŸ“Š  REGISTRAR CSV", accent_color="#8B5CF6")
        self.btn_output_csv.setCheckable(True)
        self.btn_output_csv.toggled.connect(self._toggle_output_csv)
        sidebar_layout.addWidget(self.btn_output_csv)
        
        sidebar_layout.addStretch()

        self.sidebar_footer = QLabel("Sistema v2.0  â€¢  Multimodal")
        self.sidebar_footer.setObjectName("sidebar_footer")
        self.sidebar_footer.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.sidebar_footer)

        # â”€â”€ ÃREA CENTRAL (Gerenciador de Abas) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget)

        # â•â•â•â•â•â•â•â•â•â•â•â• TELA 0: DASHBOARD â•â•â•â•â•â•â•â•â•â•â•â•
        self.page_dashboard = QFrame()
        self.page_dashboard.setObjectName("central_content")
        dash_layout = QVBoxLayout(self.page_dashboard)
        dash_layout.setContentsMargins(28, 22, 28, 0)
        dash_layout.setSpacing(18)

        header_dash = QHBoxLayout()
        app_title = QLabel("DASHBOARD PRINCIPAL")
        app_title.setObjectName("app_title")
        header_dash.addWidget(app_title)
        header_dash.addStretch()

        # HUD Indicators Group
        self.hud_container = QFrame()
        self.hud_container.setStyleSheet("background:rgba(26, 26, 38, 0.6); border-radius:15px; border:1px solid #2B2B3E;")
        hud_lyt = QHBoxLayout(self.hud_container)
        hud_lyt.setContentsMargins(15, 5, 15, 5)
        hud_lyt.setSpacing(20)

        self.arduino_indicator = QLabel("â— ARDUINO: OFF")
        self.arduino_indicator.setStyleSheet("color:#EF4444; font-weight:bold; font-size:11px;")
        
        self.eeg_indicator = QLabel("â— EEG: OFF")
        self.eeg_indicator.setStyleSheet("color:#EF4444; font-weight:bold; font-size:11px;")

        self.fps_indicator = QLabel("â— FPS: 0")
        self.fps_indicator.setStyleSheet("color:#7D7D9C; font-weight:bold; font-size:11px;")

        hud_lyt.addWidget(self.arduino_indicator)
        hud_lyt.addWidget(self.eeg_indicator)
        hud_lyt.addWidget(self.fps_indicator)
        
        header_dash.addWidget(self.hud_container)
        dash_layout.addLayout(header_dash)

        # Conectar sinais do Hub para o HUD
        self.hub.arduino_status_signal.connect(self.update_arduino_hud)
        self.hub.fps_signal.connect(self.update_fps_hud)
        self.hub.eeg_signal.connect(self.update_eeg_hud)
        
        # Estado Inicial
        self.update_arduino_hud(self.hub.arduino.board is not None)

        # DASHBOARD SUB-PAGES MANAGER
        self.dash_stack = QStackedWidget()
        dash_layout.addWidget(self.dash_stack)

        # â”€â”€ SUBTELA 0: IDLE â”€â”€
        self.dash_idle = QFrame()
        idle_layout = QVBoxLayout(self.dash_idle)
        lbl_idle = QLabel("NENHUM INPUT SELECIONADO\n\nAtive a CÃ¢mera, Luva ou Tiara EEG na barra lateral.")
        lbl_idle.setObjectName("lbl_idle")
        lbl_idle.setAlignment(Qt.AlignCenter)
        idle_layout.addWidget(lbl_idle)
        self.dash_stack.addWidget(self.dash_idle)

        # â”€â”€ SUBTELA 1: CÃ‚MERA â”€â”€
        self.dash_cam = QFrame()
        cam_layout = QVBoxLayout(self.dash_cam)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(18)

        self.video_container = QFrame()
        self.video_container.setObjectName("videopanel")
        self.video_container.setMinimumHeight(440)
        video_outer = QVBoxLayout(self.video_container)
        video_outer.setContentsMargins(0, 0, 0, 0)
        video_outer.setSpacing(0)
        video_outer.addWidget(_panel_header("CÃ¢mera Inteligente (MediaPipe)", "#3B82F6", t))

        self.video_display = VideoDisplay()
        self.hub.frame_signal.connect(self.video_display.update_frame)
        video_outer.addWidget(self.video_display)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.video_container.setGraphicsEffect(shadow)
        cam_layout.addWidget(self.video_container)

        self.cam_data = QFrame()
        self.cam_data.setObjectName("datapanel")
        cam_data_layout = QHBoxLayout(self.cam_data)
        cam_data_layout.setContentsMargins(16, 14, 16, 14)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.gesture_display = GestureDisplay()
        cam_data_layout.addWidget(self.gesture_display)

        text_col = QVBoxLayout()
        text_col.setSpacing(8)
        self.result_label = QLabel("AGUARDANDO GESTO")
        self.result_label.setStyleSheet(f"font-size:36px; font-weight:bold; color:{t['text_bright']};")
        text_col.addWidget(self.result_label)
        self.source_label = QLabel("Fonte: â€”")
        self.source_label.setStyleSheet("color:#E94560; font-weight:bold; font-size:12px; letter-spacing:1px;")
        text_col.addWidget(self.source_label)
        text_col.addSpacing(16)
        
        text_col.addWidget(_section_label("VisÃ£o FluÃ­da de MÃ£o (MediaPipe)"))
        cam_tel_layout = QVBoxLayout()
        cam_tel_layout.setSpacing(6)
        self.cam_bars = []
        for fname in ["Polegar", "Indicador", "MÃ©dio", "Anelar", "MÃ­nimo"]:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(fname)
            lbl.setFixedWidth(68)
            lbl.setObjectName("dim_label")
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            row.addWidget(lbl)
            row.addWidget(bar)
            cam_tel_layout.addLayout(row)
            self.cam_bars.append(bar)
            
        text_col.addLayout(cam_tel_layout)
        text_col.addStretch()
        cam_data_layout.addLayout(text_col)
        cam_layout.addWidget(self.cam_data)

        self.dash_stack.addWidget(self.dash_cam)

        # â”€â”€ SUBTELA 2: LUVA SENSORIAL â”€â”€
        self.dash_glove = QFrame()
        glove_layout = QHBoxLayout(self.dash_glove)
        glove_layout.setContentsMargins(0, 0, 0, 0)
        glove_layout.setSpacing(18)

        self.glove_panel = QFrame()
        self.glove_panel.setObjectName("datapanel")
        g_outer = QVBoxLayout(self.glove_panel)
        g_outer.setContentsMargins(0, 0, 0, 0)
        g_outer.setSpacing(0)
        g_outer.addWidget(_panel_header("Telemetria da Luva Ã“ptica (5DT)", "#10B981", t))

        self.glove_telemetry = QFrame()
        glove_tel_layout = QVBoxLayout(self.glove_telemetry)
        glove_tel_layout.setContentsMargins(40, 40, 40, 40)
        glove_tel_layout.setSpacing(25)

        self.glove_bars = []
        self.glove_raw_labels = []
        for i, fname in enumerate(["Polegar", "Indicador", "MÃ©dio", "Anelar", "MÃ­nimo"]):
            row = QHBoxLayout()
            row.setSpacing(15)
            lbl = QLabel(fname)
            lbl.setFixedWidth(100)
            lbl.setObjectName("app_title")
            bar = QProgressBar()
            bar.setFixedHeight(24)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            
            raw_lbl = QLabel("0.00")
            raw_lbl.setFixedWidth(40)
            raw_lbl.setStyleSheet(f"font-family:'Consolas', monospace; font-size:12px; font-weight:bold; color:{t['text_dim']};")
            
            # Spinbox de multiplicador de peso do dedo
            spin = QDoubleSpinBox()
            spin.setRange(0.1, 5.0)
            spin.setSingleStep(0.1)
            spin.setDecimals(1)
            spin.setSuffix(" x")
            spin.setFixedWidth(60)
            spin.setValue(self.hub.glove_weights[i])
            spin.valueChanged.connect(lambda v, idx=i: self.hub.set_glove_weight(idx, v))
            
            row.addWidget(lbl)
            row.addWidget(bar)
            row.addWidget(raw_lbl)
            row.addWidget(spin)
            glove_tel_layout.addLayout(row)
            self.glove_bars.append(bar)
            self.glove_raw_labels.append(raw_lbl)

        g_outer.addWidget(self.glove_telemetry)
        g_outer.addStretch()
        glove_layout.addWidget(self.glove_panel, 2)

        # Novo Painel Direito: DiagnÃ³stico da Luva
        self.glove_diag = QFrame()
        self.glove_diag.setObjectName("datapanel")
        gd_outer = QVBoxLayout(self.glove_diag)
        gd_outer.setContentsMargins(0, 0, 0, 0)
        gd_outer.setSpacing(0)
        gd_outer.addWidget(_panel_header("PrediÃ§Ã£o (I.A. Vetorial)", "#8B5CF6", t))
        
        gd_inner = QVBoxLayout()
        gd_inner.setContentsMargins(16, 14, 16, 14)
        gd_inner.setSpacing(10)
        
        self.glove_gesture_display = GestureDisplay()
        gd_inner.addWidget(self.glove_gesture_display, alignment=Qt.AlignCenter)
        
        self.glove_result_lbl = QLabel("SEM SINAL")
        self.glove_result_lbl.setStyleSheet(f"font-size:24px; font-weight:bold; color:{t['text_bright']};")
        self.glove_result_lbl.setAlignment(Qt.AlignCenter)
        gd_inner.addWidget(self.glove_result_lbl)
        
        gd_inner.addStretch()
        has_calib = len(self.hub.calibrated_vectors) > 0
        self.glove_calib_lbl = QLabel("CalibraÃ§Ã£o carregada do disco." if has_calib else "Requer CalibraÃ§Ã£o Inicial")
        color_calib = "#10B981" if has_calib else "#EF4444"
        self.glove_calib_lbl.setStyleSheet(f"font-size:10px; color:{color_calib}; font-weight:bold; font-family:'Consolas', monospace;")
        self.glove_calib_lbl.setAlignment(Qt.AlignCenter)
        gd_inner.addWidget(self.glove_calib_lbl)
        
        gd_outer.addLayout(gd_inner)
        glove_layout.addWidget(self.glove_diag, 1)

        self.dash_stack.addWidget(self.dash_glove)

        # â”€â”€ SUBTELA 3: EEG BRAINLINK â”€â”€
        self.dash_eeg = QFrame()
        eeg_layout = QVBoxLayout(self.dash_eeg)
        eeg_layout.setContentsMargins(0, 0, 0, 0)
        eeg_layout.setSpacing(18)

        eeg_split = QHBoxLayout()
        eeg_split.setSpacing(18)

        self.eeg_graph_panel = QFrame()
        self.eeg_graph_panel.setObjectName("datapanel")
        gp_outer = QVBoxLayout(self.eeg_graph_panel)
        gp_outer.setContentsMargins(0,0,0,0)
        gp_outer.setSpacing(0)

        # Header com toggle buttons
        header_bar = QWidget()
        header_bar.setFixedHeight(36)
        header_bar.setObjectName("panel_header")
        header_lyt = QHBoxLayout(header_bar)
        header_lyt.setContentsMargins(14, 0, 14, 0)
        
        dot = QLabel("â—")
        dot.setStyleSheet("color:#3B82F6; font-size:9px; margin-right:6px;")
        header_lyt.addWidget(dot)
        lbl_title = QLabel("ELETROENCEFALOGRAMA VIVO")
        lbl_title.setObjectName("panel_title")
        header_lyt.addWidget(lbl_title)
        header_lyt.addStretch()

        self.btn_view_neurosky = QPushButton("NeuroSky")
        self.btn_view_custom = QPushButton("Custom")
        self.btn_view_spectro = QPushButton("Espectrograma")
        for btn in [self.btn_view_neurosky, self.btn_view_custom, self.btn_view_spectro]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet("background:transparent; color:#A7A7C6; border:1px solid #3A3A52; border-radius:4px; padding:0 12px; font-size:10px; font-weight:bold;")
        
        self.btn_view_neurosky.setStyleSheet("background:#3B82F6; color:#FFFFFF; border:none; border-radius:4px; padding:0 12px; font-size:10px; font-weight:bold;")
        self.btn_view_neurosky.clicked.connect(lambda: self._switch_eeg_view(0))
        self.btn_view_custom.clicked.connect(lambda: self._switch_eeg_view(1))
        self.btn_view_spectro.clicked.connect(lambda: self._switch_eeg_view(2))
        header_lyt.addWidget(self.btn_view_neurosky)
        header_lyt.addWidget(self.btn_view_custom)
        header_lyt.addWidget(self.btn_view_spectro)

        gp_outer.addWidget(header_bar)

        # Stacked Widget para as duas visualizaÃ§Ãµes
        self.eeg_wave_stack = QStackedWidget()

        # === PÃGINA 0: NeuroSky (AtenÃ§Ã£o + MeditaÃ§Ã£o) ===
        page_neurosky = QWidget()
        ns_lyt = QVBoxLayout(page_neurosky)
        ns_lyt.setContentsMargins(25, 25, 25, 25)
        ns_lyt.setSpacing(15)

        lbl_att_g = QLabel("Onda de Foco (AtenÃ§Ã£o)")
        lbl_att_g.setStyleSheet("color:#EF4444; font-weight:bold; font-size:12px; letter-spacing:1px;")
        self.attn_plot = WavePlotWidget("#EF4444")
        ns_lyt.addWidget(lbl_att_g)
        ns_lyt.addWidget(self.attn_plot)
        ns_lyt.addSpacing(10)

        lbl_med_g = QLabel("Onda de Relaxamento (MeditaÃ§Ã£o)")
        lbl_med_g.setStyleSheet("color:#3B82F6; font-weight:bold; font-size:12px; letter-spacing:1px;")
        self.med_plot = WavePlotWidget("#3B82F6")
        ns_lyt.addWidget(lbl_med_g)
        ns_lyt.addWidget(self.med_plot)

        self.eeg_wave_stack.addWidget(page_neurosky)

        # === PÃGINA 1: Custom Metrics (4 ondas) ===
        page_custom = QWidget()
        cm_lyt = QVBoxLayout(page_custom)
        cm_lyt.setContentsMargins(25, 15, 25, 15)
        cm_lyt.setSpacing(6)

        custom_wave_defs = [
            ("Foco Real (Beta/Alpha)", "#EF4444", "foco_real"),
            ("Relaxamento Real (Alpha/Beta)", "#3B82F6", "relaxamento_real"),
            ("SonolÃªncia (Theta/Alpha)", "#8B5CF6", "sonolencia"),
            ("Engajamento (Beta/(Alpha+Theta))", "#F59E0B", "engajamento"),
        ]
        self.custom_plots = {}
        for label_text, color, key in custom_wave_defs:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color:{color}; font-weight:bold; font-size:10px; letter-spacing:1px;")
            plot = WavePlotWidget(color)
            plot.setMinimumHeight(70)
            cm_lyt.addWidget(lbl)
            cm_lyt.addWidget(plot)
            self.custom_plots[key] = plot

        self.eeg_wave_stack.addWidget(page_custom)

        # === PÃGINA 2: Espectrograma Heatmap ===
        page_spectro = QWidget()
        spectro_lyt = QVBoxLayout(page_spectro)
        spectro_lyt.setContentsMargins(15, 10, 15, 10)
        self.spectro_plot = SpectrogramWidget()
        spectro_lyt.addWidget(self.spectro_plot)
        self.eeg_wave_stack.addWidget(page_spectro)

        gp_outer.addWidget(self.eeg_wave_stack)
        eeg_split.addWidget(self.eeg_graph_panel, 2)

        self.eeg_ctrl_panel = QFrame()
        self.eeg_ctrl_panel.setObjectName("datapanel")
        cp_outer = QVBoxLayout(self.eeg_ctrl_panel)
        cp_outer.setContentsMargins(0,0,0,0)
        cp_outer.setSpacing(0)
        cp_outer.addWidget(_panel_header("Motor / Hub Qualidade", "#F59E0B", t))

        cp_inner = QVBoxLayout()
        cp_inner.setContentsMargins(20, 20, 20, 20)
        cp_inner.setSpacing(25)

        self.eeg_card_sig = QFrame()
        self.eeg_card_sig.setObjectName("datapanel")
        sig_lyt = QVBoxLayout(self.eeg_card_sig)
        sig_lyt.setContentsMargins(15, 15, 15, 15)
        self.eeg_label = QLabel("SINAL: DESCONECTADO")
        self.eeg_label.setAlignment(Qt.AlignCenter)
        self.eeg_label.setStyleSheet("color:#F59E0B; font-family:'Consolas', monospace; font-size:14px; font-weight:bold;")
        sig_lyt.addWidget(self.eeg_label)

        cp_inner.addWidget(self.eeg_card_sig)

        mode_lbl = QLabel("MODO DE ATUAÃ‡ÃƒO:")
        mode_lbl.setObjectName("app_title")
        cp_inner.addWidget(mode_lbl)

        self.mode_group = QButtonGroup(self.dash_eeg)
        self.rb_none = QRadioButton("Mudo (Leitura Pura)")
        self.rb_attn = QRadioButton("Foco Concentrado (>60)")
        self.rb_med = QRadioButton("Transe/MeditaÃ§Ã£o (>60)")
        self.rb_custom_focus = QRadioButton("Foco Real (Proporcional)")
        for rb in [self.rb_none, self.rb_attn, self.rb_med, self.rb_custom_focus]:
            self.mode_group.addButton(rb)
            cp_inner.addWidget(rb)
        
        self.rb_none.setChecked(True)
        self.rb_none.toggled.connect(lambda c: self._set_eeg_mode('none') if c else None)
        self.rb_attn.toggled.connect(lambda c: self._set_eeg_mode('attention') if c else None)
        self.rb_med.toggled.connect(lambda c: self._set_eeg_mode('meditation') if c else None)
        self.rb_custom_focus.toggled.connect(lambda c: self._set_eeg_mode('foco_real') if c else None)

        cp_inner.addSpacing(15)

        # Amplificador de Sensibilidade EEG
        gain_lbl = QLabel("AMPLIFICADOR:")
        gain_lbl.setObjectName("app_title")
        cp_inner.addWidget(gain_lbl)
        
        gain_row = QHBoxLayout()
        gain_row.setSpacing(8)
        self.eeg_gain_spin = QDoubleSpinBox()
        self.eeg_gain_spin.setRange(1.0, 5.0)
        self.eeg_gain_spin.setSingleStep(0.5)
        self.eeg_gain_spin.setDecimals(1)
        self.eeg_gain_spin.setSuffix(" x")
        self.eeg_gain_spin.setValue(self.hub.eeg_gain)
        self.eeg_gain_spin.valueChanged.connect(self._set_eeg_gain)
        gain_desc = QLabel("Sensibilidade dos sinais")
        gain_desc.setObjectName("dim_label")
        gain_row.addWidget(self.eeg_gain_spin)
        gain_row.addWidget(gain_desc)
        gain_row.addStretch()
        cp_inner.addLayout(gain_row)

        # SuavizaÃ§Ã£o EMA
        smooth_row = QHBoxLayout()
        smooth_row.setSpacing(8)
        self.eeg_smooth_spin = QDoubleSpinBox()
        self.eeg_smooth_spin.setRange(0.0, 0.95)
        self.eeg_smooth_spin.setSingleStep(0.05)
        self.eeg_smooth_spin.setDecimals(2)
        self.eeg_smooth_spin.setValue(self.hub.eeg_smoothing)
        self.eeg_smooth_spin.valueChanged.connect(self._set_eeg_smoothing)
        smooth_desc = QLabel("SuavizaÃ§Ã£o (0=bruto, 0.95=liso)")
        smooth_desc.setObjectName("dim_label")
        smooth_row.addWidget(self.eeg_smooth_spin)
        smooth_row.addWidget(smooth_desc)
        smooth_row.addStretch()
        cp_inner.addLayout(smooth_row)

        cp_inner.addSpacing(15)
        self.btn_test_eeg = QPushButton("ðŸŽ¯ INICIAR DESAFIO (60s)")
        self.btn_test_eeg.setCursor(Qt.PointingHandCursor)
        self.btn_test_eeg.setStyleSheet("background-color:#8B5CF6; color:#FFFFFF; border:none; border-radius:6px; padding:12px; font-weight:bold; font-size:12px;")
        self.btn_test_eeg.clicked.connect(self.start_eeg_test)
        
        self.eeg_test_lbl = QLabel("Avalie seu limite de Foco cerebral.")
        self.eeg_test_lbl.setAlignment(Qt.AlignCenter)
        self.eeg_test_lbl.setWordWrap(True)
        self.eeg_test_lbl.setStyleSheet("font-size:11px; font-weight:bold; color:#A7A7C6; padding-top:4px;")
        
        cp_inner.addWidget(self.btn_test_eeg)
        cp_inner.addWidget(self.eeg_test_lbl)

        cp_inner.addStretch()

        attn_row = QHBoxLayout()
        self.attn_label = QLabel("ATT")
        self.attn_label.setFixedWidth(40)
        self.attn_label.setObjectName("app_title")
        self.attn_bar = QProgressBar()
        self.attn_bar.setObjectName("attn_bar")
        self.attn_bar.setFixedHeight(12)
        self.attn_bar.setRange(0, 100)
        self.attn_bar.setTextVisible(False)
        attn_row.addWidget(self.attn_label)
        attn_row.addWidget(self.attn_bar)
        cp_inner.addLayout(attn_row)

        med_row = QHBoxLayout()
        self.med_label = QLabel("MED")
        self.med_label.setFixedWidth(40)
        self.med_label.setObjectName("app_title")
        self.med_bar = QProgressBar()
        self.med_bar.setObjectName("med_bar")
        self.med_bar.setFixedHeight(12)
        self.med_bar.setRange(0, 100)
        self.med_bar.setTextVisible(False)
        med_row.addWidget(self.med_label)
        med_row.addWidget(self.med_bar)
        cp_inner.addLayout(med_row)

        cp_inner.addSpacing(10)
        custom_lbl = QLabel("MÃ‰TRICAS CUSTOMIZADAS:")
        custom_lbl.setObjectName("app_title")
        cp_inner.addWidget(custom_lbl)

        self.custom_metric_bars = {}
        self.custom_metric_labels = {}
        metric_colors = {
            "foco_real": ("#EF4444", "FOCO"),
            "relaxamento_real": ("#3B82F6", "RELAX"),
            "sonolencia": ("#8B5CF6", "SONO"),
            "engajamento": ("#F59E0B", "ENGAJ"),
        }
        for key, (color, label_text) in metric_colors.items():
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(48)
            lbl.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold; font-family:'Consolas', monospace;")
            bar = QProgressBar()
            bar.setFixedHeight(10)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"QProgressBar {{background-color:#2B2B3E; border-radius:5px;}} QProgressBar::chunk {{background-color:{color}; border-radius:5px;}}")
            val_lbl = QLabel("0")
            val_lbl.setFixedWidth(28)
            val_lbl.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold; font-family:'Consolas', monospace;")
            row.addWidget(lbl)
            row.addWidget(bar)
            row.addWidget(val_lbl)
            cp_inner.addLayout(row)
            self.custom_metric_bars[key] = bar
            self.custom_metric_labels[key] = val_lbl

        cp_outer.addLayout(cp_inner)
        eeg_split.addWidget(self.eeg_ctrl_panel, 1)

        eeg_layout.addLayout(eeg_split)
        self.dash_stack.addWidget(self.dash_eeg)

        # â”€â”€ SUBTELA 4: CONTROLE MANUAL â”€â”€
        self.dash_manual = QFrame()
        manual_lyt = QVBoxLayout(self.dash_manual)
        manual_lyt.setContentsMargins(30, 20, 30, 20)
        
        manual_header = QVBoxLayout()
        manual_title = QLabel("BIBLIOTECA DE GESTOS")
        manual_title.setStyleSheet("font-size:24px; font-weight:bold; color:#8B5CF6;")
        manual_subtitle = QLabel("Acionamento direto dos servos para posiÃ§Ãµes prÃ©-programadas")
        manual_subtitle.setStyleSheet("color:#7D7D9C; font-size:12px; margin-bottom:15px;")
        manual_header.addWidget(manual_title)
        manual_header.addWidget(manual_subtitle)
        manual_lyt.addLayout(manual_header)
        
        # Grid de Gestos
        gesture_grid = QGridLayout()
        gesture_grid.setSpacing(20)
        
        gestures_ui = [
            ("ABRIR TUDO", "ðŸ–", "#3B82F6"),
            ("FECHAR TUDO", "âœŠ", "#EF4444"),
            ("JOIA (UP)", "ðŸ‘", "#10B981"),
            ("PAZ E AMOR", "âœŒï¸", "#F59E0B"),
            ("APONTAR", "â˜ï¸", "#3B82F6"),
            ("PINÃ‡A (PREC.)", "ðŸ¤", "#8B5CF6"),
            ("OK (PINÃ‡A)", "ðŸ‘Œ", "#10B981"),
            ("VULCANO", "ðŸ––", "#F59E0B"),
        ]
        
        for i, (name, emoji, color) in enumerate(gestures_ui):
            btn = QPushButton(f"{emoji}\n{name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(160, 100)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1E1E2E; color: #FFFFFF;
                    border: 2px solid #2B2B3E; border-radius: 12px;
                    font-size: 14px; font-weight: bold; padding: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color}22; border-color: {color};
                }}
                QPushButton:pressed {{
                    background-color: {color};
                }}
            """)
            btn.clicked.connect(lambda checked=False, n=name: self.hub.send_manual_gesture(n))
            gesture_grid.addWidget(btn, i // 4, i % 4)
            
        manual_lyt.addLayout(gesture_grid)
        manual_lyt.addStretch()
        self.dash_stack.addWidget(self.dash_manual)

        self.stacked_widget.addWidget(self.page_dashboard)


        # â•â•â•â•â•â•â•â•â•â•â•â• TELA 1: CONFIGURAÃ‡Ã•ES E HARDWARE â•â•â•â•â•â•â•â•â•â•â•â•
        self.page_settings = QFrame()
        self.page_settings.setObjectName("central_content")
        sett_layout = QHBoxLayout(self.page_settings)
        sett_layout.setContentsMargins(40, 40, 40, 40)
        sett_layout.setSpacing(40)

        # -- PAINEL ESQUERDO (Controladores) --
        left_panel = QVBoxLayout()
        left_panel.setSpacing(24)

        sett_header = QHBoxLayout()
        lbl_sett = QLabel("RECURSOS DO SISTEMA")
        lbl_sett.setObjectName("app_title")
        sett_header.addWidget(lbl_sett)
        sett_header.addStretch()

        self.btn_theme_toggle = QPushButton(t['toggle_label'])
        self.btn_theme_toggle.setFixedHeight(28)
        self.btn_theme_toggle.setStyleSheet(t['toggle_style'])
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        sett_header.addWidget(self.btn_theme_toggle)
        left_panel.addLayout(sett_header)
        left_panel.addWidget(_h_divider("#1E1E34"))

        # ConexÃ£o Arduino
        left_panel.addWidget(_section_label("ConexÃ£o RobÃ³tica (Arduino)"))
        port_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setFixedHeight(36)
        self.port_combo.setMinimumWidth(250)
        self.port_combo.setStyleSheet(f"""
            QComboBox {{ background-color:{t['input_bg']}; color:{t['input_color']}; border:1px solid {t['border']}; border-radius:6px; padding:5px 8px; font-size:14px; margin-right: 10px; }}
            QComboBox QAbstractItemView {{ background-color:{t['input_bg']}; color:{t['input_color']}; selection-background-color:#3B82F6; selection-color:#FFFFFF; }}
        """)

        self.eeg_port_combo = QComboBox()
        self.eeg_port_combo.setFixedHeight(36)
        self.eeg_port_combo.setMinimumWidth(180)
        self.eeg_port_combo.setStyleSheet(self.port_combo.styleSheet())
        
        self._refresh_ports_combo()
        
        self.port_combo.currentTextChanged.connect(self._update_arduino_port)
        self.eeg_port_combo.currentTextChanged.connect(self._update_eeg_port)

        port_row.addWidget(self.port_combo)
        port_row.addSpacing(20)
        port_row.addWidget(QLabel("PORTA EEG:"))
        port_row.addWidget(self.eeg_port_combo)
        
        self.btn_auto_ports = ActionButton("ðŸ” DETECTAR", color="#8B5CF6")
        self.btn_auto_ports.setFixedHeight(36) # ForÃ§ando a altura para bater com a combobox
        self.btn_auto_ports.clicked.connect(self._on_auto_detect_clicked)
        port_row.addWidget(self.btn_auto_ports)
        port_row.addStretch()
        left_panel.addLayout(port_row)

        self.btn_test_hand = ActionButton("âš™ï¸ TESTAR CONEXÃƒO", color="#3B82F6")
        self.btn_test_hand.clicked.connect(self.hub.test_arduino_hand)
        left_panel.addWidget(self.btn_test_hand, alignment=Qt.AlignLeft)
        left_panel.addSpacing(16)

        # CalibraÃ§Ã£o
        left_panel.addWidget(_section_label("Sensores FÃ­sicos"))
        self.btn_calibrate_glove = ActionButton("ðŸ– REFAZER CALIBRAÃ‡ÃƒO DA LUVA", color="#10B981")
        self.btn_calibrate_glove.clicked.connect(self.start_calibration_sequence)
        left_panel.addWidget(self.btn_calibrate_glove, alignment=Qt.AlignLeft)
        left_panel.addSpacing(16)

        # EmergÃªncia
        left_panel.addWidget(_section_label("Zona de Perigo"))
        self.btn_stop = ActionButton("ðŸ›‘ CORTE DE EMERGÃŠNCIA DOS MOTORES", color="#EF4444")
        self.btn_stop.clicked.connect(self.hub.stop)
        left_panel.addWidget(self.btn_stop, alignment=Qt.AlignLeft)
        
        left_panel.addStretch()

        # -- PAINEL DIREITO (Terminal de Logs) --
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)
        right_panel.addWidget(_section_label("Console de Sistema Local (Debug ao Vivo)"))
        
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setLineWrapMode(QTextEdit.NoWrap)
        t = self._current_theme()
        self.log_terminal.setStyleSheet(f"""
            QTextEdit {{
                background-color:#0A0A0F; color:#A7A7C6; 
                border:1px solid {t['border']}; border-radius:6px; 
                padding:12px; font-family:'Consolas', monospace; font-size:11px;
            }}
        """)
        right_panel.addWidget(self.log_terminal)

        # Junta as metades horizontais alocando mais peso (3) para o terminal crescer
        sett_layout.addLayout(left_panel, 2)
        sett_layout.addLayout(right_panel, 3)

        self.stacked_widget.addWidget(self.page_settings)

        # â”€â”€ BARRA DE STATUS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.status_bar_label = QLabel("â— SISTEMA INICIADO")
        self.status_bar_label.setObjectName("status_bar")
        right_layout.addWidget(self.status_bar_label)

        main_layout.addWidget(self.sidebar, 1)
        main_layout.addWidget(right_container, 3)

        self._switch_tab(0)

    # â”€â”€ Callbacks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ #
    def _refresh_ports_combo(self):
        self.port_combo.blockSignals(True)
        self.eeg_port_combo.blockSignals(True)
        self.port_combo.clear()
        self.eeg_port_combo.clear()
        
        from outputs.arduino_output import ArduinoOutput
        ports = ArduinoOutput.list_available_ports()
        
        saved_arduino = self.hub.config.get("arduino_port", "COM5")
        saved_eeg = self.hub.config.get("eeg_port", "")
        
        idx_arduino = -1
        idx_eeg = -1
        
        for i, port_info in enumerate(ports):
            port_name = port_info.split(' ')[0]
            self.port_combo.addItem(port_info, port_name)
            self.eeg_port_combo.addItem(port_info, port_name)
            
            if port_name == saved_arduino: idx_arduino = i
            if port_name == saved_eeg: idx_eeg = i
                
        if not ports:
            self.port_combo.addItem(f"{saved_arduino} (OFF)", saved_arduino)
            self.eeg_port_combo.addItem(f"{saved_eeg} (OFF)", saved_eeg)
            idx_arduino = 0
            idx_eeg = 0

        if idx_arduino >= 0: self.port_combo.setCurrentIndex(idx_arduino)
        if idx_eeg >= 0: self.eeg_port_combo.setCurrentIndex(idx_eeg)
            
        self.port_combo.blockSignals(False)
        self.eeg_port_combo.blockSignals(False)
        
        if self.port_combo.currentData():
            self.hub.arduino.port = self.port_combo.currentData()

    def _on_auto_detect_clicked(self):
        self.status_bar_label.setText("â— BUSCANDO HARDWARE...")
        self.hub.auto_detect_all_ports()

    def _on_discovery_finished(self, success):
        self._refresh_ports_combo()
        msg = "Dispositivos Encontrados" if success else "Nenhum dispositivo encontrado"
        self.status_bar_label.setText(f"â— {msg.upper()}")
        self._refresh_ports_combo()

    def _update_arduino_port(self, text):
        real_port = self.port_combo.currentData()
        if not real_port: real_port = text.split(' ')[0]
        if self.hub.arduino:
            self.hub.arduino.port = real_port
            self.hub.config.set("arduino_port", real_port)
            self.update_status_bar(f"Porta Arduino: {real_port}")

    def _update_eeg_port(self, text):
        real_port = self.eeg_port_combo.currentData()
        if not real_port: real_port = text.split(' ')[0]
        self.hub.config.set("eeg_port", real_port)
        self.update_status_bar(f"Porta EEG: {real_port}")

    def _toggle_output_hand(self, checked):
        if checked:
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
            self.hub.set_hand_output(True)
        else:
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
            self.hub.set_hand_output(False)

    def _toggle_output_csv(self, checked):
        if checked:
            self.btn_output_csv.setText("ðŸ“Š  GRAVANDO CSV")
            self.btn_output_csv._accent_color = "#10B981"
            self.btn_output_csv._update_style(checked=True)
            self.hub.status_signal.emit("GravaÃ§Ã£o CSV Iniciada (Simulado)")
        else:
            self.btn_output_csv.setText("ðŸ“Š  REGISTRAR CSV")
            self.btn_output_csv._accent_color = "#8B5CF6"
            self.btn_output_csv._update_style(checked=False)
            self.hub.status_signal.emit("GravaÃ§Ã£o CSV Parada")

    def _toggle_camera(self, checked):
        if checked:
            self.btn_glove.setChecked(False)
            self.btn_eeg.setChecked(False)
            self.btn_manual.setChecked(False)
            self.dash_stack.setCurrentIndex(1)
        else:
            if not (self.btn_glove.isChecked() or self.btn_eeg.isChecked() or self.btn_manual.isChecked()):
                self.dash_stack.setCurrentIndex(0)
        self.btn_cam._update_style(checked)
        self.hub.set_camera_active(checked)

    def _toggle_glove(self, checked):
        if checked:
            self.btn_cam.setChecked(False)
            self.btn_eeg.setChecked(False)
            self.btn_manual.setChecked(False)
            self.dash_stack.setCurrentIndex(2)
        else:
            if not (self.btn_cam.isChecked() or self.btn_eeg.isChecked() or self.btn_manual.isChecked()):
                self.dash_stack.setCurrentIndex(0)
        self.btn_glove._update_style(checked)
        self.hub.set_glove_active(checked)

    def _toggle_eeg(self, checked):
        if checked:
            self.btn_cam.setChecked(False)
            self.btn_glove.setChecked(False)
            self.btn_manual.setChecked(False)
            self.dash_stack.setCurrentIndex(3)
        else:
            if not (self.btn_cam.isChecked() or self.btn_glove.isChecked() or self.btn_manual.isChecked()):
                self.dash_stack.setCurrentIndex(0)
        self.btn_eeg._update_style(checked)
        self.hub.set_eeg_active(checked)

    def _toggle_manual(self, checked):
        if checked:
            self.btn_cam.setChecked(False)
            self.btn_glove.setChecked(False)
            self.btn_eeg.setChecked(False)
            self.dash_stack.setCurrentIndex(4)
        else:
            if not (self.btn_cam.isChecked() or self.btn_glove.isChecked() or self.btn_eeg.isChecked()):
                self.dash_stack.setCurrentIndex(0)
        self.btn_manual._update_style(checked)
        self.hub.status_signal.emit("Modo Manual ATIVADO" if checked else "Modo Manual DESATIVADO")

    def _set_eeg_mode(self, mode):
        self.hub.eeg_control_mode = mode

    def _set_eeg_gain(self, value):
        self.hub.eeg_gain = value
        self.hub.config.set("eeg_gain", value)

    def _set_eeg_smoothing(self, value):
        self.hub.eeg_smoothing = value
        self.hub.config.set("eeg_smoothing", value)

    def _switch_eeg_view(self, idx):
        self.eeg_wave_stack.setCurrentIndex(idx)
        valido = "background:#3B82F6; color:#FFFFFF; border:none; border-radius:4px; padding:0 12px; font-size:10px; font-weight:bold;"
        invalido = "background:transparent; color:#A7A7C6; border:1px solid #3A3A52; border-radius:4px; padding:0 12px; font-size:10px; font-weight:bold;"
        self.btn_view_neurosky.setStyleSheet(valido if idx == 0 else invalido)
        self.btn_view_custom.setStyleSheet(valido if idx == 1 else invalido)
        self.btn_view_spectro.setStyleSheet(valido if idx == 2 else invalido)

    def update_status_bar(self, message):
        self.status_bar_label.setText(f"â— {message.upper()}")

    def update_glove_data(self, data):
        sensors = data.get("sensors", [])
        thresholds = getattr(self.hub, "clinical_thresholds", [])
        
        for i, val in enumerate(sensors[:5]):
            if i < len(self.glove_bars):
                self.glove_bars[i].setValue(int(val * 100))
                
                # Se tivermos threshold clÃ­nico, mostra no label
                if len(thresholds) > i:
                    t_val = thresholds[i]
                    self.glove_raw_labels[i].setText(f"{val:.2f} (T:{t_val:.2f})")
                    self.glove_raw_labels[i].setFixedWidth(100) # Expande para caber o threshold
                else:
                    self.glove_raw_labels[i].setText(f"{val:.2f}")

    def update_prediction(self, data):
        t = self._current_theme()
        gid    = data.get("gesture_id", -1)
        pred   = data.get("prediction", "N/A")
        conf   = data.get("confidence", 0)
        source = data.get("source", "UNKNOWN")
        fingers = data.get("fingers", None)

        print(f"*** UI RECEIVE: {pred} FROM {source} ***")

        self.result_label.setText(pred)
        self.source_label.setText(f"FONTE: {source}  Â·  {conf}%")
        self.gesture_display.update_gesture(gid)

        color = "#10B981" if conf > 85 else t['text_bright']
        self.result_label.setStyleSheet(f"font-size:36px; font-weight:bold; color:{color};")

        if fingers and source == "CAMERA":
            keys = ['polegar', 'indicador', 'medio', 'anelar', 'minimo']
            for i, k in enumerate(keys):
                if i < len(self.cam_bars):
                    val = fingers.get(k, 0)
                    if k == 'polegar': 
                        pct = val
                    else:
                        pct = max(0, min(100, (val - 60) / 120 * 100))
                    self.cam_bars[i].setValue(int(pct))
        elif source == "GLOVE":
            self.glove_result_lbl.setText(pred)
            self.glove_gesture_display.update_gesture(gid)
            color = "#10B981" if conf > 85 else t['text_bright']
            self.glove_result_lbl.setStyleSheet(f"font-size:24px; font-weight:bold; color:{color};")

    def start_eeg_test(self):
        self.eeg_test_active = True
        self.eeg_test_phase = 1
        self.eeg_test_seconds = 30
        self.max_focus = 0
        self.max_meditation = 0
        self.eeg_test_lbl.setText("FASE 1: MAXIMIZE SEU FOCO! (30s)")
        self.eeg_test_lbl.setStyleSheet("color:#EF4444; font-size:14px; font-weight:bold;")
        self.eeg_timer.start(1000)
        self.btn_test_eeg.setEnabled(False)
        self.btn_test_eeg.setStyleSheet("background-color:#4B5563; color:#9CA3AF; border-radius:6px; padding:12px; font-weight:bold; font-size:12px;")

    def _eeg_test_tick(self):
        self.eeg_test_seconds -= 1
        if self.eeg_test_seconds <= 0:
            if self.eeg_test_phase == 1:
                self.eeg_test_phase = 2
                self.eeg_test_seconds = 30
                self.eeg_test_lbl.setText("FASE 2: RELAXE PROFUNDAMENTE! (30s)")
                self.eeg_test_lbl.setStyleSheet("color:#3B82F6; font-size:14px; font-weight:bold;")
            else:
                self.eeg_timer.stop()
                self.eeg_test_active = False
                self.eeg_test_lbl.setText(f"ðŸ† Foco: {self.max_focus}%  |  Relaxe: {self.max_meditation}%")
                self.eeg_test_lbl.setStyleSheet("color:#10B981; font-size:13px; font-weight:bold;")
                self.btn_test_eeg.setEnabled(True)
                self.btn_test_eeg.setText("ðŸ”„ REINICIAR DESAFIO")
                self.btn_test_eeg.setStyleSheet("background-color:#8B5CF6; color:#FFFFFF; border-radius:6px; padding:12px; font-weight:bold; font-size:12px;")
        else:
            if self.eeg_test_phase == 1:
                self.eeg_test_lbl.setText(f"FASE 1: MAXIMIZE SEU FOCO! ({self.eeg_test_seconds}s)")
            else:
                self.eeg_test_lbl.setText(f"FASE 2: RELAXE PROFUNDAMENTE! ({self.eeg_test_seconds}s)")

    def update_eeg_data(self, data):
        # ProteÃ§Ã£o contra chamadas antes da UI estar pronta
        if not hasattr(self, 'attn_bar') or not hasattr(self, 'custom_metric_bars'):
            return

        att = data.get("attention", 0)
        med = data.get("meditation", 0)
        sig = data.get("signal", 200)

        # Log diagnÃ³stico refinado (apenas quando hÃ¡ sinal)
        if sig < 200:
             print(f"DEBUG UI EEG: Data flow active -> Att:{att} Med:{med} Sig:{sig}")

        # GamificaÃ§Ã£o State Machine Hook
        if getattr(self, "eeg_test_active", False):
            if self.eeg_test_phase == 1 and att > self.max_focus:
                self.max_focus = att
            elif self.eeg_test_phase == 2 and med > self.max_meditation:
                self.max_meditation = med

        self.attn_bar.setValue(att)
        self.med_bar.setValue(med)
        
        if hasattr(self, 'attn_plot'):
            self.attn_plot.add_value(att)
            self.med_plot.add_value(med)

        # Custom Wave Plots
        custom = data.get("custom_metrics", {})
        if hasattr(self, 'custom_plots'):
            for key, plot in self.custom_plots.items():
                val = int(custom.get(key, 0))
                plot.add_value(val)

        # Custom Metric Bars
        for key, bar in self.custom_metric_bars.items():
            val = int(custom.get(key, 0))
            bar.setValue(val)
            if key in self.custom_metric_labels:
                self.custom_metric_labels[key].setText(str(val))

        # Spectrogram Update
        waves = data.get("waves", {})
        if hasattr(self, 'spectro_plot'):
            self.spectro_plot.add_data(waves)

        status_text = "CONEXÃƒO LIMPA" if sig < 50 else ("FALHANDO" if sig < 200 else "DISPOSITIVO OFF")
        self.eeg_label.setText(f"SINAL {sig:3d}\n{status_text}")

        color = "#10B981" if sig < 50 else ("#F59E0B" if sig < 200 else "#EF4444")
        self.eeg_label.setStyleSheet(
            f"color:{color}; font-family:'Consolas', monospace; font-size:14px; font-weight:bold;"
        )

    def update_arduino_hud(self, connected):
        color = "#10B981" if connected else "#EF4444"
        self.arduino_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:11px;")
        self.arduino_indicator.setText(f"â— ARDUINO: {'OK' if connected else 'OFF'}")

    def update_fps_hud(self, fps):
        color = "#10B981" if fps > 22 else ("#F59E0B" if fps > 12 else "#EF4444")
        self.fps_indicator.setText(f"â— FPS: {int(fps)}")
        self.fps_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:11px;")

    def update_eeg_hud(self, data):
        sig = data.get("signal", 200)
        color = "#10B981" if sig < 50 else ("#F59E0B" if sig < 200 else "#EF4444")
        text = "FORTE" if sig < 50 else ("MÃ‰DIO" if sig < 200 else "SEM SINAL")
        self.eeg_indicator.setText(f"â— EEG: {text}")
        self.eeg_indicator.setStyleSheet(f"color:{color}; font-weight:bold; font-size:11px;")




    def toggle_sidebar(self):
        width = self.sidebar.width()
        is_collapsed = width < 100 # Se for menor que 100, estÃ¡ colapsado agora
        
        new_width = 268 if is_collapsed else 72
        
        # AnimaÃ§Ã£o de suavidade
        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(250)
        self.animation.setStartValue(width)
        self.animation.setEndValue(new_width)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        
        self.animation2 = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.animation2.setDuration(250)
        self.animation2.setStartValue(width)
        self.animation2.setEndValue(new_width)
        self.animation2.setEasingCurve(QEasingCurve.InOutQuart)
        
        self.animation.start()
        self.animation2.start()
        
        # Esconder/Mostrar elementos baseado na largura final
        target_visible = is_collapsed # Se vai expandir (new=268), fica visÃ­vel
        
        # Lista de widgets/layouts que devem sumir no modo mini
        labels_to_hide = [
             self.nav_container, self.brand_widget, self.lbl_inputs, self.lbl_outputs, self.sidebar_footer
        ]
        
        for item in labels_to_hide:
            if hasattr(item, "setVisible"):
                item.setVisible(target_visible)
        
        # Ajusta os botÃµes de input para sumir o texto e ficar sÃ³ Ã­cone
        inputs = [self.btn_cam, self.btn_glove, self.btn_eeg, self.btn_manual, self.btn_output_hand, self.btn_output_csv]
        for btn in inputs:
            orig_text = btn.text()
            if not is_collapsed: # Vai colapsar
                if "  " in orig_text:
                    btn._full_text = orig_text
                    btn.setText(orig_text.split("  ")[0]) # Deixa sÃ³ o Ã­cone (ex: ðŸŽ¥)
            else: # Vai expandir
                if hasattr(btn, "_full_text"):
                    btn.setText(btn._full_text)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
