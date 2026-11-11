from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ui.components.controls import Segmented, StatusChip
from ui.icons import set_icon


class NavHeader(QFrame):
    """
    Cabeçalho global: marca, seletor de fonte (Câmera / Luva / EEG),
    chips de status do hardware e botões de tema e configurações.
    """
    theme_toggled = Signal()
    settings_clicked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(60)
        self._theme = None
        self._is_dark = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(16)

        # ── Marca ────────────────────────────────────────────────
        brand = QHBoxLayout()
        brand.setSpacing(10)
        self.logo_badge = QFrame()
        self.logo_badge.setObjectName("logo_badge")
        self.logo_badge.setFixedSize(32, 32)
        badge_lyt = QHBoxLayout(self.logo_badge)
        badge_lyt.setContentsMargins(0, 0, 0, 0)
        self.logo_icon = QPushButton()
        self.logo_icon.setFlat(True)
        self.logo_icon.setEnabled(False)
        self.logo_icon.setStyleSheet("background:transparent; border:none; min-height:0; padding:0;")
        self.logo_icon.setIconSize(QSize(18, 18))
        badge_lyt.addWidget(self.logo_icon, 0, Qt.AlignCenter)
        brand.addWidget(self.logo_badge)

        names = QVBoxLayout()
        names.setSpacing(0)
        self.title_label = QLabel("Mão Robótica")
        self.title_label.setObjectName("app_name")
        self.tagline_label = QLabel("Controle multimodal")
        self.tagline_label.setObjectName("app_tagline")
        names.addWidget(self.title_label)
        names.addWidget(self.tagline_label)
        brand.addLayout(names)
        layout.addLayout(brand)

        layout.addStretch(1)

        # ── Seletor de fonte de controle ─────────────────────────
        self.mode_selector = Segmented(["Câmera", "Luva 5DT", "EEG"], exclusive=False)
        self.btn_cam, self.btn_glove, self.btn_eeg = self.mode_selector.buttons
        self.btn_cam.setToolTip("Ligar/desligar o rastreamento por câmera")
        self.btn_glove.setToolTip("Ligar/desligar a luva sensorial 5DT")
        self.btn_eeg.setToolTip("Ligar/desligar a tiara EEG BrainLink")
        layout.addWidget(self.mode_selector, 0, Qt.AlignVCenter)

        layout.addStretch(1)

        # ── Status do hardware ───────────────────────────────────
        self.arduino_indicator = StatusChip("Arduino desconectado", "danger")
        self.eeg_indicator = StatusChip("EEG desligado", "off")
        self.fps_indicator = StatusChip("0 fps", "mono")
        for chip in (self.arduino_indicator, self.eeg_indicator, self.fps_indicator):
            layout.addWidget(chip, 0, Qt.AlignVCenter)

        # ── Ações globais ────────────────────────────────────────
        self.btn_theme = QPushButton()
        self.btn_theme.setProperty("variant", "icon")
        self.btn_theme.setFixedSize(36, 36)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setToolTip("Alternar tema claro/escuro")
        self.btn_theme.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self.btn_theme)

        self.btn_settings = QPushButton()
        self.btn_settings.setProperty("variant", "icon")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("Configurações de hardware e console")
        self.btn_settings.toggled.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

    def update_theme(self, is_dark, colors):
        """Recolore ícones e chips conforme o tema."""
        self._theme = colors
        self._is_dark = is_dark
        set_icon(self.logo_icon, "hand", colors["accent_strong"], 18)
        set_icon(self.btn_theme, "sun" if is_dark else "moon", colors["text_muted"], 16)
        set_icon(self.btn_settings, "settings", colors["text_muted"], 16)
        set_icon(self.btn_cam, "camera", colors["text_muted"], 16)
        set_icon(self.btn_glove, "hand", colors["text_muted"], 16)
        set_icon(self.btn_eeg, "activity", colors["text_muted"], 16)
        for chip in (self.arduino_indicator, self.eeg_indicator, self.fps_indicator):
            chip.set_theme(colors)

    # ── Telemetria ───────────────────────────────────────────────
    def set_arduino_status(self, connected):
        self._arduino_connected = bool(connected)
        port = getattr(self, "_arduino_port", "")
        if connected:
            self.arduino_indicator.set_state("ok", f"Arduino · {port}" if port else "Arduino conectado")
        else:
            self.arduino_indicator.set_state("danger", "Arduino desconectado")

    def set_arduino_port(self, port):
        self._arduino_port = port or ""
        self.set_arduino_status(getattr(self, "_arduino_connected", False))

    def set_fps(self, fps):
        self.fps_indicator.set_state("mono", f"{int(fps)} fps")

    def set_eeg_quality(self, signal):
        # signal 0-200 (quanto menor, melhor)
        if signal < 50:
            self.eeg_indicator.set_state("ok", "EEG · sinal bom")
        elif signal < 200:
            self.eeg_indicator.set_state("warn", "EEG · sinal fraco")
        else:
            self.eeg_indicator.set_state("danger", "EEG · sem sinal")

    def set_eeg_off(self):
        self.eeg_indicator.set_state("off", "EEG desligado")
