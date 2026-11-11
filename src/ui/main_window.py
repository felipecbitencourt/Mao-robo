import sys

from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.hub_controller import HubController
from ui.components.controls import Segmented, SwitchRow, card, divider, label
from ui.components.gesture_display import GestureDisplay
from ui.components.hand_output import FINGER_KEYS, FINGER_NAMES, HandOutputWidget, normalize_fingers
from ui.components.nav_header import NavHeader
from ui.components.spectrogram_widget import SpectrogramWidget
from ui.components.video_display import VideoDisplay
from ui.components.wave_plot import WavePlotWidget  # noqa: F401 (reexportado por compatibilidade)
from ui.icons import set_icon
from ui.theme import build_stylesheet, get_theme, repolish

# Índices das páginas
DASH_IDLE, DASH_CAM, DASH_GLOVE, DASH_EEG = range(4)
PAGE_DASHBOARD, PAGE_SETTINGS = range(2)

EEG_MODES = [
    ("none", "Só leitura"),
    ("attention", "Atenção"),
    ("meditation", "Meditação"),
    ("foco_real", "Foco real (β)"),
]

CUSTOM_METRICS = [
    ("foco_real", "Foco real", "β / espectro total", 1),
    ("relaxamento_real", "Relaxamento", "α / β", 2),
    ("sonolencia", "Sonolência", "θ / α", 3),
    ("engajamento", "Engajamento", "β / (α + θ)", 4),
]


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


def _bar(series=None, size=None):
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setTextVisible(False)
    if series:
        bar.setProperty("series", str(series))
    if size:
        bar.setProperty("size", size)
    return bar


def _page_title(title, caption):
    box = QVBoxLayout()
    box.setSpacing(2)
    box.addWidget(label(title, name="h1"))
    box.addWidget(label(caption, name="caption"))
    return box


# ══════════════════════════════════════════════════════════════════
#  Janela principal
# ══════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hub = HubController()
        self.setWindowTitle("Mão Robótica")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 700)
        self._dark_mode = self.hub.config.get("theme_dark_mode", True)
        self._last_status = ""

        self.hub.status_signal.connect(self.update_status_bar)
        self.hub.prediction_signal.connect(self.update_prediction)
        self.hub.glove_signal.connect(self.update_glove_data)
        self.hub.eeg_signal.connect(self.update_eeg_data)
        self.hub.discovery_finished_signal.connect(self._on_discovery_finished)
        self.hub.eeg_lost_signal.connect(self._on_eeg_lost)

        # Desafio EEG (60 s)
        self.eeg_test_active = False
        self.eeg_test_phase = 0
        self.eeg_test_seconds = 0
        self.max_focus = 0
        self.max_meditation = 0
        self.eeg_timer = QTimer(self)
        self.eeg_timer.timeout.connect(self._eeg_test_tick)

        # Calibração clínica (10 ciclos)
        self.clin_cal_active = False
        self.clin_cal_cycle = 0
        self.clin_cal_phase = 0  # 0: aguardando, 1: OPEN, 2: CLOSED
        self.clin_cal_seconds = 0
        self.clin_timer = QTimer(self)
        self.clin_timer.timeout.connect(self._clin_cal_tick)

        self._init_ui()
        self._apply_theme()

        # Logs do processo vão também para o console da tela de configurações
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

    # ── Tema ──────────────────────────────────────────────────── #
    def _current_theme(self):
        return get_theme(self._dark_mode)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.hub.config.set("theme_dark_mode", self._dark_mode)
        self._apply_theme()

    def _apply_theme(self):
        t = self._current_theme()
        app = QApplication.instance()
        (app or self).setStyleSheet(build_stylesheet(t))

        self.header.update_theme(self._dark_mode, t)
        set_icon(self.btn_stop, "stop", t["danger_text"], 18)
        set_icon(self.btn_open_console, "terminal", t["text_muted"], 14)
        set_icon(self.btn_back_dashboard, "arrow_left", t["text_secondary"], 16)
        set_icon(self.btn_refresh_cams, "refresh", t["text_secondary"], 16)
        set_icon(self.btn_auto_ports, "search", t["text_secondary"], 16)
        set_icon(self.btn_test_hand, "play", t["text_secondary"], 14)
        set_icon(self.btn_test_eeg, "target", t["text_secondary"], 16)
        for btn, name in self._idle_buttons:
            set_icon(btn, name, t["text_secondary"], 18)
        self.status_icon.setPixmap(self._status_icon_pixmap(t))

        self.hand_output.set_theme(t)
        self.switch_hand.switch.set_theme(t)
        self.switch_csv.switch.set_theme(t)
        self.spectro_plot.set_theme(t)

        grid = t["track"] if not self._dark_mode else "#20242C"
        self.neuro_plot.update_theme("#00000000", grid, t["text_muted"])
        self.neuro_plot.set_series_color("attention", t["series_1"])
        self.neuro_plot.set_series_color("meditation", t["series_2"])
        for key, plot in self.custom_plots.items():
            plot.update_theme("#00000000", grid, t["text_muted"])
            plot.set_series_color("default", t[f"series_{self._custom_series[key]}"])
        self._refresh_legend()

    def _status_icon_pixmap(self, t):
        from ui.icons import icon
        return icon("terminal", t["text_muted"], 14).pixmap(QSize(14, 14))

    # ── Navegação ─────────────────────────────────────────────── #
    def _switch_tab(self, idx):
        self.stacked_widget.setCurrentIndex(idx)
        self.header.btn_settings.blockSignals(True)
        self.header.btn_settings.setChecked(idx == PAGE_SETTINGS)
        self.header.btn_settings.blockSignals(False)

    def _on_settings_clicked(self, checked):
        self._switch_tab(PAGE_SETTINGS if checked else PAGE_DASHBOARD)

    # ── Calibração clínica (10 ciclos) ────────────────────────── #
    def start_calibration_sequence(self):
        """Inicia o protocolo clínico de 10 ciclos"""
        self.btn_calibrate_glove.setEnabled(False)
        self.clin_cal_active = True
        self.clin_cal_cycle = 1
        self.clin_cal_phase = 1  # começa com OPEN
        self.clin_cal_seconds = 5

        self.hub.status_signal.emit("Iniciando protocolo clínico (10 ciclos)...")
        self._update_clin_cal_ui()
        self.clin_timer.start(1000)

    def _clin_cal_tick(self):
        if not self.clin_cal_active:
            return

        self.clin_cal_seconds -= 1

        # No primeiro tick de cada estágio (5 -> 4) avisa o Hub para capturar
        if self.clin_cal_seconds == 4:
            stage = 'OPEN' if self.clin_cal_phase == 1 else 'CLOSED'
            self.hub.start_clinical_step(stage)

        if self.clin_cal_seconds <= 0:
            self.hub.stop_clinical_step()

            if self.clin_cal_phase == 1:
                self.clin_cal_phase = 2
                self.clin_cal_seconds = 5
            else:
                if self.clin_cal_cycle >= 10:
                    self.finish_calibration_ui()
                    return
                self.clin_cal_cycle += 1
                self.clin_cal_phase = 1
                self.clin_cal_seconds = 5

        self._update_clin_cal_ui()

    def _update_clin_cal_ui(self):
        msg = "Abra a mão completamente" if self.clin_cal_phase == 1 else "Feche a mão completamente"
        self.calib_step_lbl.setText(msg)
        self.calib_detail_lbl.setText(f"Ciclo {self.clin_cal_cycle} de 10 · {self.clin_cal_seconds} s")
        done_steps = (self.clin_cal_cycle - 1) * 2 + (self.clin_cal_phase - 1)
        self.calib_progress.setValue(int(done_steps / 20 * 100))

    def finish_calibration_ui(self):
        self.clin_cal_active = False
        self.clin_timer.stop()

        success = self.hub.calculate_clinical_final()

        self.btn_calibrate_glove.setEnabled(True)
        self.calib_progress.setValue(100 if success else 0)
        if success:
            self.calib_step_lbl.setText("Calibração concluída")
            self.calib_detail_lbl.setText("Limiares clínicos salvos no perfil.")
            self._set_calib_status(True)
            self.hub.status_signal.emit("Protocolo finalizado com sucesso!")
        else:
            self.calib_step_lbl.setText("Erro na calibração")
            self.calib_detail_lbl.setText("Nenhuma amostra válida. Confira a luva e tente de novo.")

    def _set_calib_status(self, ok):
        level = "ok" if ok else "warn"
        self.glove_calib_lbl.set_state(level, "Calibrada" if ok else "Precisa calibrar")

    def closeEvent(self, event):
        print("Fechando aplicação... parando threads.")
        self.hub.stop()
        # Devolve stdout/stderr originais: o console da janela deixa de existir
        sys.stdout = self.stdout_redirector.stream
        sys.stderr = self.stderr_redirector.stream
        event.accept()

    # ══════════════════════════════════════════════════════════════
    #  Construção da UI
    # ══════════════════════════════════════════════════════════════
    def _init_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Cabeçalho ────────────────────────────────────────────
        self.header = NavHeader(self)
        self.header.theme_toggled.connect(self._toggle_theme)
        self.header.settings_clicked.connect(self._on_settings_clicked)
        outer.addWidget(self.header)

        self.btn_cam = self.header.btn_cam
        self.btn_glove = self.header.btn_glove
        self.btn_eeg = self.header.btn_eeg
        self.btn_cam.toggled.connect(self._toggle_camera)
        self.btn_glove.toggled.connect(self._toggle_glove)
        self.btn_eeg.toggled.connect(self._toggle_eeg)

        self.hub.arduino_status_signal.connect(self.header.set_arduino_status)
        self.hub.fps_signal.connect(self.header.set_fps)
        self.hub.eeg_signal.connect(self._on_eeg_quality)
        if hasattr(self.hub, 'arduino'):
            self.header.set_arduino_port(getattr(self.hub.arduino, "port", ""))
            self.header.set_arduino_status(self.hub.arduino.board is not None)

        # ── Corpo: área principal + painel de saída ─────────────
        body = QWidget()
        body_lyt = QHBoxLayout(body)
        body_lyt.setContentsMargins(20, 16, 20, 16)
        body_lyt.setSpacing(16)
        outer.addWidget(body, 1)

        self.stacked_widget = QStackedWidget()
        body_lyt.addWidget(self.stacked_widget, 1)

        self.page_dashboard = QWidget()
        self.page_dashboard.setObjectName("page")
        dash_lyt = QVBoxLayout(self.page_dashboard)
        dash_lyt.setContentsMargins(0, 0, 0, 0)
        self.dash_stack = QStackedWidget()
        dash_lyt.addWidget(self.dash_stack)

        self.dash_stack.addWidget(self._build_idle_page())
        self.dash_stack.addWidget(self._build_camera_page())
        self.dash_stack.addWidget(self._build_glove_page())
        self.dash_stack.addWidget(self._build_eeg_page())
        self.stacked_widget.addWidget(self.page_dashboard)
        self.stacked_widget.addWidget(self._build_settings_page())

        body_lyt.addWidget(self._build_output_panel())

        # ── Barra de status ──────────────────────────────────────
        status = QFrame()
        status.setObjectName("statusbar")
        status.setFixedHeight(40)
        st_lyt = QHBoxLayout(status)
        st_lyt.setContentsMargins(20, 0, 16, 0)
        st_lyt.setSpacing(10)
        self.status_icon = QLabel()
        st_lyt.addWidget(self.status_icon)
        self.status_bar_label = label("Sistema iniciado", name="status_text")
        self.status_bar_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        st_lyt.addWidget(self.status_bar_label, 1)
        self.btn_open_console = QPushButton("Console")
        self.btn_open_console.setProperty("variant", "ghost")
        self.btn_open_console.setCursor(Qt.PointingHandCursor)
        self.btn_open_console.setObjectName("console_btn")
        self.btn_open_console.clicked.connect(lambda: self._switch_tab(PAGE_SETTINGS))
        st_lyt.addWidget(self.btn_open_console)
        outer.addWidget(status)

        # Esc = parar motores, em qualquer tela
        self.stop_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.stop_shortcut.setContext(Qt.ApplicationShortcut)
        self.stop_shortcut.activated.connect(self._emergency_stop)

        self._refresh_ports_combo()
        self._refresh_camera_list()
        self._switch_tab(PAGE_DASHBOARD)

    # ── Tela vazia ───────────────────────────────────────────── #
    def _build_idle_page(self):
        page = QWidget()
        page.setObjectName("page")
        lyt = QVBoxLayout(page)
        lyt.addStretch(1)

        box, box_lyt = card(padding=32, spacing=10)
        box.setMaximumWidth(560)
        box_lyt.addWidget(label("Escolha uma fonte de controle", name="empty_title"))
        box_lyt.addWidget(label(
            "A mão robótica pode seguir a câmera, a luva sensorial ou a tiara EEG. "
            "Ligue uma delas para começar; dá para trocar a qualquer momento pelo seletor no topo.",
            name="caption", wrap=True))
        box_lyt.addSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(10)
        self._idle_buttons = []
        for text, icon_name, target in (("Câmera", "camera", self.btn_cam),
                                        ("Luva 5DT", "hand", self.btn_glove),
                                        ("EEG", "activity", self.btn_eeg)):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda _=False, b=target: b.setChecked(True))
            row.addWidget(btn)
            self._idle_buttons.append((btn, icon_name))
        box_lyt.addLayout(row)

        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(box)
        h.addStretch(1)
        lyt.addLayout(h)
        lyt.addStretch(2)
        return page

    # ── Câmera ───────────────────────────────────────────────── #
    def _build_camera_page(self):
        self.dash_cam = QWidget()
        self.dash_cam.setObjectName("page")
        lyt = QVBoxLayout(self.dash_cam)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(12)

        top = QHBoxLayout()
        top.addLayout(_page_title("Rastreamento por câmera", "MediaPipe · 21 pontos da mão"), 1)
        self.cam_view_selector = Segmented(["Câmera única", "Visão dual"], size="sm")
        self.cam_view_selector.set_current(0)
        self.btn_dual_vision = self.cam_view_selector.buttons[1]
        self.btn_dual_vision.setToolTip("Combina duas câmeras para reduzir oclusão")
        self.btn_dual_vision.toggled.connect(self._toggle_dual_vision)
        top.addWidget(self.cam_view_selector, 0, Qt.AlignVCenter)
        lyt.addLayout(top)

        self.video_container = QFrame()
        self.video_container.setObjectName("video_frame")
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(8, 8, 8, 8)
        self.video_layout.setSpacing(8)
        self.video_display = VideoDisplay()
        self.video_display2 = VideoDisplay()
        self.video_display2.setVisible(False)
        self.video_layout.addWidget(self.video_display)
        self.video_layout.addWidget(self.video_display2)
        self.hub.frame_signal.connect(self._handle_processed_frame)
        lyt.addWidget(self.video_container, 1)
        return self.dash_cam

    # ── Luva ─────────────────────────────────────────────────── #
    def _build_glove_page(self):
        self.dash_glove = QWidget()
        self.dash_glove.setObjectName("page")
        lyt = QVBoxLayout(self.dash_glove)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(12)

        lyt.addLayout(_page_title("Luva sensorial 5DT", "Leitura dos sensores ópticos e peso de cada dedo"))

        sensors, s_lyt = card(padding=20, spacing=14)
        head = QHBoxLayout()
        head.addWidget(label("Sensores", name="h2"), 1)
        head.addWidget(label("Peso", role="muted"))
        s_lyt.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(1, 1)
        self.glove_bars = []
        self.glove_raw_labels = []
        self.glove_weight_spins = []
        for i, fname in enumerate(FINGER_NAMES):
            name_lbl = label(fname, role="finger")
            name_lbl.setMinimumWidth(80)
            bar = _bar(size="lg")
            raw_lbl = label("0.00", role="mono_muted")
            raw_lbl.setMinimumWidth(120)
            raw_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            spin = QDoubleSpinBox()
            spin.setRange(0.1, 5.0)
            spin.setSingleStep(0.1)
            spin.setDecimals(1)
            spin.setSuffix(" ×")
            spin.setFixedWidth(84)
            spin.setValue(self.hub.glove_weights[i])
            spin.setToolTip(f"Multiplicador do sensor do {fname.lower()}")
            spin.valueChanged.connect(lambda v, idx=i: self.hub.set_glove_weight(idx, v))

            grid.addWidget(name_lbl, i, 0)
            grid.addWidget(bar, i, 1)
            grid.addWidget(raw_lbl, i, 2)
            grid.addWidget(spin, i, 3)
            self.glove_bars.append(bar)
            self.glove_raw_labels.append(raw_lbl)
            self.glove_weight_spins.append(spin)
        s_lyt.addLayout(grid)
        lyt.addWidget(sensors)

        calib, c_lyt = card(padding=20, spacing=10)
        head = QHBoxLayout()
        head.addWidget(label("Calibração clínica", name="h2"), 1)
        from ui.components.controls import StatusChip
        self.glove_calib_lbl = StatusChip("", "off")
        head.addWidget(self.glove_calib_lbl)
        c_lyt.addLayout(head)
        c_lyt.addWidget(label(
            "10 ciclos de abrir e fechar a mão, 5 s cada. Os limiares ficam salvos no perfil.",
            name="caption", wrap=True))
        self.calib_step_lbl = label("Pronta para começar", role="finger")
        self.calib_step_lbl.setStyleSheet("font-size:15px; font-weight:600;")
        self.calib_detail_lbl = label("", name="caption")
        self.calib_progress = _bar()
        c_lyt.addWidget(self.calib_step_lbl)
        c_lyt.addWidget(self.calib_detail_lbl)
        c_lyt.addWidget(self.calib_progress)
        btn_row = QHBoxLayout()
        self.btn_calibrate_glove = QPushButton("Calibrar luva")
        self.btn_calibrate_glove.setProperty("variant", "primary")
        self.btn_calibrate_glove.setCursor(Qt.PointingHandCursor)
        self.btn_calibrate_glove.clicked.connect(self.start_calibration_sequence)
        btn_row.addWidget(self.btn_calibrate_glove)
        btn_row.addStretch(1)
        c_lyt.addLayout(btn_row)
        lyt.addWidget(calib)
        lyt.addStretch(1)

        has_calib = len(self.hub.calibrated_vectors) > 0 or len(getattr(self.hub, "clinical_thresholds", [])) > 0
        self._set_calib_status(has_calib)
        return self.dash_glove

    # ── EEG ──────────────────────────────────────────────────── #
    def _build_eeg_page(self):
        self.dash_eeg = QWidget()
        self.dash_eeg.setObjectName("page")
        outer = QVBoxLayout(self.dash_eeg)
        outer.setContentsMargins(0, 0, 0, 0)

        self.eeg_scroll = QScrollArea()
        self.eeg_scroll.setWidgetResizable(True)
        self.eeg_scroll.setFrameShape(QFrame.NoFrame)
        self.eeg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("page")
        self.eeg_scroll.setWidget(content)
        outer.addWidget(self.eeg_scroll)

        lyt = QVBoxLayout(content)
        lyt.setContentsMargins(0, 0, 4, 0)
        lyt.setSpacing(12)

        top = QHBoxLayout()
        top.addLayout(_page_title("Controle por EEG",
                                  "BrainLink · atenção fecha a mão; meditação e foco real abrem"), 1)
        self.eeg_view_selector = Segmented(["Ondas", "Métricas", "Espectrograma"], size="sm")
        self.eeg_view_selector.set_current(0)
        self.eeg_view_selector.group.idClicked.connect(self._switch_eeg_view)
        top.addWidget(self.eeg_view_selector, 0, Qt.AlignVCenter)
        lyt.addLayout(top)

        # Gráficos
        graph, g_lyt = card(padding=18, spacing=12)
        legend_row = QHBoxLayout()
        legend_row.setSpacing(18)
        self.legend_lbl = QLabel()
        self.legend_lbl.setTextFormat(Qt.RichText)
        legend_row.addWidget(self.legend_lbl, 1)
        self.eeg_label = label("Sem sinal", role="mono_muted")
        legend_row.addWidget(self.eeg_label)
        g_lyt.addLayout(legend_row)

        self.eeg_wave_stack = QStackedWidget()
        self.eeg_wave_stack.setMinimumHeight(300)

        self.neuro_plot = WavePlotWidget()
        self.neuro_plot.add_series("attention", "#F59E4B")
        self.neuro_plot.add_series("meditation", "#60A5FA")
        self.attn_plot = self.neuro_plot  # compatibilidade
        self.med_plot = self.neuro_plot
        self.eeg_wave_stack.addWidget(self.neuro_plot)

        page_custom = QWidget()
        cm = QGridLayout(page_custom)
        cm.setContentsMargins(0, 0, 0, 0)
        cm.setHorizontalSpacing(16)
        cm.setVerticalSpacing(6)
        self.custom_plots = {}
        self._custom_series = {}
        for i, (key, name, formula, series) in enumerate(CUSTOM_METRICS):
            r, c = divmod(i, 2)
            cell = QVBoxLayout()
            cell.setSpacing(4)
            cell.addWidget(label(f"{name}  ·  {formula}", name="caption"))
            plot = WavePlotWidget()
            plot.setMinimumHeight(110)
            cell.addWidget(plot, 1)
            cm.addLayout(cell, r, c)
            self.custom_plots[key] = plot
            self._custom_series[key] = series
        self.eeg_wave_stack.addWidget(page_custom)

        self.spectro_plot = SpectrogramWidget()
        self.eeg_wave_stack.addWidget(self.spectro_plot)
        g_lyt.addWidget(self.eeg_wave_stack, 1)
        lyt.addWidget(graph, 1)

        # Controles
        ctrl, ctrl_lyt = card(padding=18, spacing=14)
        c_lyt = QHBoxLayout()
        c_lyt.setSpacing(20)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(label("O que move a mão", role="field"))
        self.eeg_mode_selector = Segmented([m[1] for m in EEG_MODES], size="sm", accent=True)
        self.eeg_mode_selector.set_current(0)
        self.eeg_mode_selector.group.idClicked.connect(lambda i: self._set_eeg_mode(EEG_MODES[i][0]))
        col.addWidget(self.eeg_mode_selector)
        c_lyt.addLayout(col)

        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(label("Ganho", role="field"))
        self.eeg_gain_spin = QDoubleSpinBox()
        self.eeg_gain_spin.setRange(1.0, 5.0)
        self.eeg_gain_spin.setSingleStep(0.5)
        self.eeg_gain_spin.setDecimals(1)
        self.eeg_gain_spin.setSuffix(" ×")
        self.eeg_gain_spin.setFixedWidth(90)
        self.eeg_gain_spin.setValue(self.hub.eeg_gain)
        self.eeg_gain_spin.setToolTip("Amplifica a sensibilidade dos sinais")
        self.eeg_gain_spin.valueChanged.connect(self._set_eeg_gain)
        col.addWidget(self.eeg_gain_spin)
        c_lyt.addLayout(col)

        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(label("Suavização", role="field"))
        self.eeg_smooth_spin = QDoubleSpinBox()
        self.eeg_smooth_spin.setRange(0.0, 0.95)
        self.eeg_smooth_spin.setSingleStep(0.05)
        self.eeg_smooth_spin.setDecimals(2)
        self.eeg_smooth_spin.setFixedWidth(90)
        self.eeg_smooth_spin.setValue(self.hub.eeg_smoothing)
        self.eeg_smooth_spin.setToolTip("0 = sinal bruto, 0.95 = bem liso")
        self.eeg_smooth_spin.valueChanged.connect(self._set_eeg_smoothing)
        col.addWidget(self.eeg_smooth_spin)
        c_lyt.addLayout(col)
        c_lyt.addStretch(1)
        ctrl_lyt.addLayout(c_lyt)
        ctrl_lyt.addWidget(divider())

        row = QHBoxLayout()
        row.setSpacing(12)
        self.btn_test_eeg = QPushButton("Desafio de 60 s")
        self.btn_test_eeg.setCursor(Qt.PointingHandCursor)
        self.btn_test_eeg.clicked.connect(self.start_eeg_test)
        row.addWidget(self.btn_test_eeg)
        self.eeg_test_lbl = label("30 s de foco máximo e 30 s de relaxamento; mostra seus picos.", name="caption", wrap=True)
        row.addWidget(self.eeg_test_lbl, 1)
        ctrl_lyt.addLayout(row)
        lyt.addWidget(ctrl)

        # Métricas
        metrics, m_lyt = card(padding=18, spacing=12)
        m_lyt.addWidget(label("Métricas ao vivo", name="h2"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        rows = [("attention", "Atenção", 1), ("meditation", "Meditação", 2)] + \
               [(k, n, s) for k, n, _, s in CUSTOM_METRICS]
        self.custom_metric_bars = {}
        self.custom_metric_labels = {}
        for i, (key, name, series) in enumerate(rows):
            r, c = i // 2, (i % 2) * 3
            name_lbl = label(name, role="finger")
            name_lbl.setMinimumWidth(96)
            bar = _bar(series=series)
            val_lbl = label("0", role="mono")
            val_lbl.setMinimumWidth(28)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(name_lbl, r, c)
            grid.addWidget(bar, r, c + 1)
            grid.addWidget(val_lbl, r, c + 2)
            if key == "attention":
                self.attn_bar, self.attn_val_lbl = bar, val_lbl
            elif key == "meditation":
                self.med_bar, self.med_val_lbl = bar, val_lbl
            else:
                self.custom_metric_bars[key] = bar
                self.custom_metric_labels[key] = val_lbl
        grid.setColumnMinimumWidth(3, 24)
        m_lyt.addLayout(grid)
        lyt.addWidget(metrics)

        self._last_att = 0
        self._last_med = 0
        return self.dash_eeg

    def _refresh_legend(self):
        t = self._current_theme()
        sw = lambda c: f'<span style="color:{c}; font-size:16px;">━</span>'
        idx = self.eeg_wave_stack.currentIndex() if hasattr(self, "eeg_wave_stack") else 0
        if idx == 0:
            html = (f'{sw(t["series_1"])}&nbsp; Atenção <b style="font-family:monospace;">{self._last_att}</b>'
                    f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sw(t["series_2"])}&nbsp; Meditação '
                    f'<b style="font-family:monospace;">{self._last_med}</b>')
        elif idx == 1:
            html = "Índices calculados a partir das 8 bandas"
        else:
            html = "Potência por banda (δ a γ) ao longo do tempo"
        self.legend_lbl.setText(f'<span style="font-size:13px; color:{t["text_secondary"]};">{html}</span>')

    # ── Configurações ─────────────────────────────────────────── #
    def _build_settings_page(self):
        self.page_settings = QWidget()
        self.page_settings.setObjectName("page")
        lyt = QVBoxLayout(self.page_settings)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(12)

        top = QHBoxLayout()
        self.btn_back_dashboard = QPushButton()
        self.btn_back_dashboard.setProperty("variant", "icon")
        self.btn_back_dashboard.setFixedSize(36, 36)
        self.btn_back_dashboard.setCursor(Qt.PointingHandCursor)
        self.btn_back_dashboard.setToolTip("Voltar ao painel")
        self.btn_back_dashboard.clicked.connect(lambda: self._switch_tab(PAGE_DASHBOARD))
        top.addWidget(self.btn_back_dashboard, 0, Qt.AlignVCenter)
        top.addSpacing(6)
        top.addLayout(_page_title("Configurações", "Portas, câmeras, calibração e console"), 1)
        lyt.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(16)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(12)

        # Portas seriais
        ports, p_lyt = card(padding=18, spacing=10)
        p_lyt.addWidget(label("Portas seriais", name="h2"))
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)
        self.port_combo = QComboBox()
        self.eeg_port_combo = QComboBox()
        form.addWidget(label("Mão robótica (Arduino)", role="field"), 0, 0)
        form.addWidget(self.port_combo, 0, 1)
        form.addWidget(label("Tiara EEG", role="field"), 1, 0)
        form.addWidget(self.eeg_port_combo, 1, 1)
        p_lyt.addLayout(form)
        btns = QHBoxLayout()
        self.btn_auto_ports = QPushButton("Detectar portas")
        self.btn_auto_ports.setCursor(Qt.PointingHandCursor)
        self.btn_auto_ports.clicked.connect(self._on_auto_detect_clicked)
        self.btn_test_hand = QPushButton("Testar servos")
        self.btn_test_hand.setCursor(Qt.PointingHandCursor)
        self.btn_test_hand.setToolTip("Roda a sequência de teste em todos os dedos")
        self.btn_test_hand.clicked.connect(self.hub.test_arduino_hand)
        btns.addWidget(self.btn_auto_ports)
        btns.addWidget(self.btn_test_hand)
        btns.addStretch(1)
        p_lyt.addLayout(btns)
        left.addWidget(ports)

        # Câmeras
        cams, cam_lyt = card(padding=18, spacing=10)
        cam_lyt.addWidget(label("Câmeras", name="h2"))
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)
        self.cam_combo = QComboBox()
        self.cam2_combo = QComboBox()
        self.cam_backend_combo = QComboBox()
        self.cam_backend_combo.addItem("DirectShow (padrão)", "dshow")
        self.cam_backend_combo.addItem("Media Foundation (MSMF)", "msmf")
        self.cam_backend_combo.blockSignals(True)
        _saved_backend = str(self.hub.config.get("camera_backend", "dshow")).lower()
        self.cam_backend_combo.setCurrentIndex(1 if _saved_backend == "msmf" else 0)
        self.cam_backend_combo.blockSignals(False)
        self.cam_backend_combo.currentIndexChanged.connect(self._on_camera_backend_changed)
        self.cam_combo.currentIndexChanged.connect(self._update_camera_index)
        self.cam2_combo.currentIndexChanged.connect(self._update_camera2_index)

        self.btn_refresh_cams = QPushButton()
        self.btn_refresh_cams.setProperty("variant", "icon")
        self.btn_refresh_cams.setFixedSize(36, 36)
        self.btn_refresh_cams.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_cams.setToolTip("Procurar câmeras de novo")
        self.btn_refresh_cams.clicked.connect(self._refresh_camera_list)

        form.addWidget(label("Principal", role="field"), 0, 0)
        form.addWidget(self.cam_combo, 0, 1)
        form.addWidget(self.btn_refresh_cams, 0, 2)
        form.addWidget(label("Secundária (visão dual)", role="field"), 1, 0)
        form.addWidget(self.cam2_combo, 1, 1)
        form.addWidget(label("Driver de vídeo", role="field"), 2, 0)
        form.addWidget(self.cam_backend_combo, 2, 1)
        cam_lyt.addLayout(form)
        left.addWidget(cams)
        left.addStretch(1)

        self.port_combo.currentTextChanged.connect(self._update_arduino_port)
        self.eeg_port_combo.currentTextChanged.connect(self._update_eeg_port)

        # Console
        console, con_lyt = card(padding=18, spacing=10)
        con_lyt.addWidget(label("Console", name="h2"))
        con_lyt.addWidget(label("Saída do programa em tempo real (stdout e stderr).", name="caption"))
        self.log_terminal = QTextEdit()
        self.log_terminal.setObjectName("console")
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setLineWrapMode(QTextEdit.NoWrap)
        # Limita o histórico do console para não crescer sem fim em sessões longas
        self.log_terminal.document().setMaximumBlockCount(2000)
        con_lyt.addWidget(self.log_terminal, 1)

        left_w = QWidget()
        left_w.setLayout(left)
        cols.addWidget(left_w, 1)
        cols.addWidget(console, 1)
        lyt.addLayout(cols, 1)
        return self.page_settings

    # ── Painel de saída (sempre visível) ─────────────────────── #
    def _build_output_panel(self):
        aside = QWidget()
        aside.setObjectName("page")
        lyt = QVBoxLayout(aside)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(12)

        # Gesto
        gest, g_lyt = card(padding=16, spacing=10)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.gesture_display = GestureDisplay(size=64)
        self.glove_gesture_display = self.gesture_display  # compatibilidade
        row.addWidget(self.gesture_display)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(label("Gesto reconhecido", name="eyebrow"))
        self.result_label = label("Aguardando", name="display")
        self.result_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.glove_result_lbl = self.result_label  # compatibilidade
        col.addWidget(self.result_label)
        self.source_label = label("Nenhuma fonte ativa", name="caption")
        col.addWidget(self.source_label)
        row.addLayout(col, 1)
        self.conf_label = label("", name="metric")
        row.addWidget(self.conf_label, 0, Qt.AlignTop)
        g_lyt.addLayout(row)
        self.conf_bar = _bar()
        g_lyt.addWidget(self.conf_bar)
        lyt.addWidget(gest)

        # Abertura dos dedos
        hand, h_lyt = card(padding=16, spacing=12)
        head = QHBoxLayout()
        head.addWidget(label("Abertura dos dedos", name="h2"), 1)
        head.addWidget(label("0 = fechado · 100 = aberto", name="caption"))
        h_lyt.addLayout(head)
        self.hand_output = HandOutputWidget()
        self.hand_output.setMinimumHeight(150)
        h_lyt.addWidget(self.hand_output)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)
        self.cam_bars = []
        self.finger_value_labels = []
        for i, name in enumerate(FINGER_NAMES):
            n = label(name, role="finger")
            n.setMinimumWidth(72)
            bar = _bar()
            v = label("—", role="mono")
            v.setMinimumWidth(40)
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(n, i, 0)
            grid.addWidget(bar, i, 1)
            grid.addWidget(v, i, 2)
            self.cam_bars.append(bar)
            self.finger_value_labels.append(v)
        h_lyt.addLayout(grid)
        lyt.addWidget(hand)

        # Saídas
        outs, o_lyt = card(padding=16, spacing=0)
        o_lyt.setContentsMargins(16, 4, 16, 4)
        self.switch_hand = SwitchRow("Enviar para a mão", "Desligado · servos parados")
        self.switch_csv = SwitchRow("Gravar sessão (CSV)", "Desligado")
        self.btn_output_hand = self.switch_hand.switch
        self.btn_output_csv = self.switch_csv.switch
        self.btn_output_hand.toggled.connect(self._toggle_output_hand)
        self.btn_output_csv.toggled.connect(self._toggle_output_csv)
        o_lyt.addWidget(self.switch_hand)
        o_lyt.addWidget(divider())
        o_lyt.addWidget(self.switch_csv)
        lyt.addWidget(outs)

        lyt.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(aside)

        # O botão de parada fica fora da rolagem: sempre visível
        self.btn_stop = QPushButton("  Parar motores   (Esc)")
        self.btn_stop.setObjectName("stop_button")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setToolTip("Corta o envio para os servos e desliga todas as entradas")
        self.btn_stop.clicked.connect(self._emergency_stop)

        column = QWidget()
        column.setFixedWidth(360)
        col_lyt = QVBoxLayout(column)
        col_lyt.setContentsMargins(0, 0, 0, 0)
        col_lyt.setSpacing(12)
        col_lyt.addWidget(scroll, 1)
        col_lyt.addWidget(self.btn_stop)
        return column

    # ══════════════════════════════════════════════════════════════
    #  Callbacks
    # ══════════════════════════════════════════════════════════════
    def _emergency_stop(self):
        """Corta a saída para os servos e desliga todas as entradas."""
        self.btn_output_hand.setChecked(False)
        for btn in (self.btn_cam, self.btn_glove, self.btn_eeg):
            btn.setChecked(False)
        self.hub.stop()
        self.update_status_bar("Parada de emergência: saída para a mão cortada")

    def _on_camera_backend_changed(self):
        b = self.cam_backend_combo.currentData()
        if b is not None:
            self.hub.config.set("camera_backend", b)
        self._refresh_camera_list()
        if self.btn_cam.isChecked():
            self.hub.set_camera_active(False)
            self.hub.set_camera_active(True)
        if self.hub.dual_vision_active:
            self.hub.set_dual_vision(False)
            self.hub.set_dual_vision(True)

    def _refresh_camera_list(self):
        self.cam_combo.blockSignals(True)
        self.cam2_combo.blockSignals(True)
        self.cam_combo.clear()
        self.cam2_combo.clear()

        from inputs.camera_input import CameraInput
        backend = (
            self.cam_backend_combo.currentData()
            if hasattr(self, "cam_backend_combo")
            else self.hub.config.get("camera_backend", "dshow")
        )
        available = CameraInput.list_cameras(backend=backend)

        saved_index = self.hub.config.get("camera_index", 0)
        saved2_index = self.hub.config.get("camera2_index", 1)
        found_saved = False
        found2_saved = False

        for idx, name in available:
            self.cam_combo.addItem(name, idx)
            self.cam2_combo.addItem(name, idx)

            if idx == saved_index:
                self.cam_combo.setCurrentIndex(self.cam_combo.count() - 1)
                found_saved = True
            if idx == saved2_index:
                self.cam2_combo.setCurrentIndex(self.cam2_combo.count() - 1)
                found2_saved = True

        if not found_saved:
            self.cam_combo.addItem(f"Câmera {saved_index} (desconectada)", saved_index)
            self.cam_combo.setCurrentIndex(self.cam_combo.count() - 1)
        if not found2_saved:
            self.cam2_combo.addItem(f"Câmera {saved2_index} (desconectada)", saved2_index)
            self.cam2_combo.setCurrentIndex(self.cam2_combo.count() - 1)

        self.cam_combo.blockSignals(False)
        self.cam2_combo.blockSignals(False)

    def _update_camera_index(self, index_ui):
        new_idx = self.cam_combo.currentData()
        if new_idx is not None:
            # Se a câmera estiver rodando, o HubController reinicia
            is_active = self.btn_cam.isChecked()
            self.hub.set_camera_active(is_active, index=new_idx)
            self.update_status_bar(f"Fonte de vídeo alterada para ID: {new_idx}")

    def _update_camera2_index(self):
        new_idx = self.cam2_combo.currentData()
        if new_idx is not None:
            is_dual = self.hub.dual_vision_active
            self.hub.set_dual_vision(is_dual, index=new_idx)
            self.update_status_bar(f"Fonte secundária alterada para ID: {new_idx}")

    def _handle_processed_frame(self, frame, source_id):
        if source_id == 0:
            self.video_display.update_frame(frame)
        else:
            self.video_display2.update_frame(frame)

    def _toggle_dual_vision(self, checked):
        self.video_display2.setVisible(checked)
        self.hub.set_dual_vision(checked)

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

            if port_name == saved_arduino:
                idx_arduino = i
            if port_name == saved_eeg:
                idx_eeg = i

        if not ports:
            self.port_combo.addItem(f"{saved_arduino} (não encontrada)", saved_arduino)
            self.eeg_port_combo.addItem(f"{saved_eeg or '—'} (não encontrada)", saved_eeg)
            idx_arduino = 0
            idx_eeg = 0

        if idx_arduino >= 0:
            self.port_combo.setCurrentIndex(idx_arduino)
        if idx_eeg >= 0:
            self.eeg_port_combo.setCurrentIndex(idx_eeg)

        self.port_combo.blockSignals(False)
        self.eeg_port_combo.blockSignals(False)

        if self.port_combo.currentData():
            self.hub.arduino.port = self.port_combo.currentData()
            self.header.set_arduino_port(self.hub.arduino.port)

    def _on_auto_detect_clicked(self):
        self.update_status_bar("Buscando hardware...")
        self.hub.auto_detect_all_ports()

    def _on_discovery_finished(self, success):
        self._refresh_ports_combo()
        self.update_status_bar("Dispositivos encontrados" if success else "Nenhum dispositivo encontrado")

    def _update_arduino_port(self, text):
        real_port = self.port_combo.currentData()
        if not real_port:
            real_port = text.split(' ')[0]
        if self.hub.arduino:
            self.hub.arduino.port = real_port
            self.hub.config.set("arduino_port", real_port)
            self.header.set_arduino_port(real_port)
            self.update_status_bar(f"Porta Arduino: {real_port}")

    def _update_eeg_port(self, text):
        real_port = self.eeg_port_combo.currentData()
        if not real_port:
            real_port = text.split(' ')[0]
        self.hub.config.set("eeg_port", real_port)
        self.update_status_bar(f"Porta EEG: {real_port}")

    def _toggle_output_hand(self, checked):
        self.switch_hand.subtitle.setText(
            "Ligado · servos seguem a abertura acima" if checked else "Desligado · servos parados")
        self.hub.set_hand_output(checked)
        self.hand_output.set_values(self.hand_output.values, active=checked)

    def _toggle_output_csv(self, checked):
        self.switch_csv.subtitle.setText("Gravando" if checked else "Desligado")
        try:
            self.hub.set_recording(checked)
        except OSError as e:
            self.hub.status_signal.emit(f"Não foi possível gravar o CSV: {e}")
            self.btn_output_csv.blockSignals(True)
            self.btn_output_csv.setChecked(False)
            self.btn_output_csv.blockSignals(False)
            self.switch_csv.subtitle.setText("Desligado")

    def _select_input(self, checked, target_page, others):
        if checked:
            for b in others:
                b.setChecked(False)
            self.dash_stack.setCurrentIndex(target_page)
            self._switch_tab(PAGE_DASHBOARD)
        elif not any(b.isChecked() for b in others):
            self.dash_stack.setCurrentIndex(DASH_IDLE)
            self._reset_output_panel()

    def _toggle_camera(self, checked):
        self._select_input(checked, DASH_CAM, (self.btn_glove, self.btn_eeg))
        self.hub.set_camera_active(checked)

    def _toggle_glove(self, checked):
        self._select_input(checked, DASH_GLOVE, (self.btn_cam, self.btn_eeg))
        self.hub.set_glove_active(checked)

    def _toggle_eeg(self, checked):
        self._select_input(checked, DASH_EEG, (self.btn_cam, self.btn_glove))
        self.hub.set_eeg_active(checked)
        if not checked:
            self.header.set_eeg_off()

    def _reset_output_panel(self):
        self.result_label.setText("Aguardando")
        self.source_label.setText("Nenhuma fonte ativa")
        self.conf_label.setText("")
        self.conf_bar.setValue(0)
        self.gesture_display.update_gesture(-1)

    def _on_eeg_lost(self):
        """A tiara caiu: desliga o botão para a UI não mostrar o EEG como ativo"""
        if self.btn_eeg.isChecked():
            self.btn_eeg.setChecked(False)
        self.update_status_bar("EEG: conexão perdida")

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
        self.eeg_view_selector.set_current(idx)
        self._refresh_legend()

    def update_status_bar(self, message):
        self._last_status = str(message)
        self.status_bar_label.setText(self._last_status)

    def update_glove_data(self, data):
        sensors = data.get("sensors", [])
        thresholds = getattr(self.hub, "clinical_thresholds", [])

        for i, val in enumerate(sensors[:5]):
            if i < len(self.glove_bars):
                self.glove_bars[i].setValue(int(val * 100))
                if len(thresholds) > i:
                    self.glove_raw_labels[i].setText(f"{val:.2f}  limiar {thresholds[i]:.2f}")
                else:
                    self.glove_raw_labels[i].setText(f"{val:.2f}")

    def update_prediction(self, data):
        gid = data.get("gesture_id", -1)
        pred = data.get("prediction", "N/A")
        conf = data.get("confidence", 0)
        source = data.get("source", "UNKNOWN")
        fingers = data.get("fingers", None)

        self.result_label.setText(str(pred))
        self.source_label.setText(self._source_name(source))
        try:
            conf_i = int(max(0, min(100, conf)))
        except (TypeError, ValueError):
            conf_i = 0
        self.conf_label.setText(f"{conf_i}%")
        self.conf_bar.setValue(conf_i)
        self.gesture_display.update_gesture(gid)

        if fingers:
            opening = data.get("opening")
            if opening:
                # Mesma abertura (0..1) que vai para o Arduino
                values = [int(round(100 * opening.get(k, 0.0))) for k in FINGER_KEYS]
            else:
                values = normalize_fingers(fingers, source)
            self.hand_output.set_values(values, active=self.btn_output_hand.isChecked())
            for bar, lbl, v in zip(self.cam_bars, self.finger_value_labels, values):
                bar.setValue(v)
                lbl.setText(f"{v}%")

    @staticmethod
    def _source_name(source):
        s = str(source)
        if s.upper().startswith("CAMERA"):
            return f"Fonte: câmera {s.split()[-1]}" if s.split()[-1].isdigit() else "Fonte: câmera"
        if s.upper().startswith("VISÃO"):
            return "Fonte: visão dual (fusão)"
        return {"GLOVE": "Fonte: luva 5DT", "EEG": "Fonte: EEG"}.get(s.upper(), f"Fonte: {s.lower()}")

    def start_eeg_test(self):
        self.eeg_test_active = True
        self.eeg_test_phase = 1
        self.eeg_test_seconds = 30
        self.max_focus = 0
        self.max_meditation = 0
        self.eeg_test_lbl.setText("Fase 1 de 2: concentre-se ao máximo (30 s)")
        self.eeg_timer.start(1000)
        self.btn_test_eeg.setEnabled(False)

    def _eeg_test_tick(self):
        self.eeg_test_seconds -= 1
        if self.eeg_test_seconds <= 0:
            if self.eeg_test_phase == 1:
                self.eeg_test_phase = 2
                self.eeg_test_seconds = 30
                self.eeg_test_lbl.setText("Fase 2 de 2: relaxe profundamente (30 s)")
            else:
                self.eeg_timer.stop()
                self.eeg_test_active = False
                self.eeg_test_lbl.setText(f"Pico de foco {self.max_focus}  ·  pico de relaxamento {self.max_meditation}")
                self.btn_test_eeg.setEnabled(True)
                self.btn_test_eeg.setText("Repetir desafio")
        else:
            if self.eeg_test_phase == 1:
                self.eeg_test_lbl.setText(f"Fase 1 de 2: concentre-se ao máximo ({self.eeg_test_seconds} s)")
            else:
                self.eeg_test_lbl.setText(f"Fase 2 de 2: relaxe profundamente ({self.eeg_test_seconds} s)")

    def _on_eeg_quality(self, data):
        if self.btn_eeg.isChecked():
            self.header.set_eeg_quality(data.get("signal", 200))

    def update_eeg_data(self, data):
        if not hasattr(self, 'attn_bar') or not hasattr(self, 'custom_metric_bars'):
            return

        att = data.get("attention", 0)
        med = data.get("meditation", 0)
        sig = data.get("signal", 200)


        if getattr(self, "eeg_test_active", False):
            if self.eeg_test_phase == 1 and att > self.max_focus:
                self.max_focus = att
            elif self.eeg_test_phase == 2 and med > self.max_meditation:
                self.max_meditation = med

        self.attn_bar.setValue(att)
        self.med_bar.setValue(med)
        self.attn_val_lbl.setText(str(att))
        self.med_val_lbl.setText(str(med))
        self.neuro_plot.add_series_value("attention", att)
        self.neuro_plot.add_series_value("meditation", med)
        self._last_att, self._last_med = att, med

        custom = data.get("custom_metrics", {})
        for key, plot in self.custom_plots.items():
            plot.add_value(int(custom.get(key, 0)))

        for key, bar in self.custom_metric_bars.items():
            val = int(custom.get(key, 0))
            bar.setValue(val)
            if key in self.custom_metric_labels:
                self.custom_metric_labels[key].setText(str(val))

        waves = data.get("waves", {})
        self.spectro_plot.add_data(waves)

        status_text = "conexão limpa" if sig < 50 else ("sinal fraco" if sig < 200 else "sem contato")
        self.eeg_label.setText(f"Sinal {sig} · {status_text}")
        self._refresh_legend()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
