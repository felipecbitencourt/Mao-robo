"""
Tokens de design e folha de estilo global da interface.

Todo o visual sai daqui: os widgets recebem um objectName ou uma
propriedade dinâmica (ex.: ``card="true"``, ``variant="ghost"``) e a
folha de estilo gerada por ``build_stylesheet`` cuida do resto. Trocar
o tema é só reaplicar a folha com outra paleta.
"""

DARK = {
    "name": "dark",
    "bg": "#0F1115",
    "header_bg": "#13161C",
    "surface": "#171A21",
    "surface_alt": "#1A1D24",
    "raised": "#2A2F3A",
    "track": "#262A33",
    "border": "#262A33",
    "border_strong": "#353B47",
    "text": "#E7E9EE",
    "text_secondary": "#C9CED8",
    "text_muted": "#9AA3B2",
    "text_faint": "#5B6270",
    "accent": "#34D1BF",
    "accent_strong": "#5EE0D0",
    "accent_soft": "#16302C",
    "accent_on": "#0F1115",
    "accent_text": "#8BEADF",
    "warn": "#F5B544",
    "warn_soft": "#33280F",
    "warn_text": "#F7CD7E",
    "danger": "#F87171",
    "danger_soft": "#3A1518",
    "danger_border": "#7F2B2B",
    "danger_text": "#FFB4B4",
    "video_bg": "#0A0C10",
    "console_bg": "#0B0D11",
    # Séries de dados (laranja x azul: distinguíveis também em luminância)
    "series_1": "#F59E4B",
    "series_2": "#60A5FA",
    "series_3": "#C4B5FD",
    "series_4": "#FCD34D",
}

LIGHT = {
    "name": "light",
    "bg": "#F5F6F8",
    "header_bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_alt": "#EEF0F3",
    "raised": "#FFFFFF",
    "track": "#E6E9EE",
    "border": "#E2E5EA",
    "border_strong": "#D5D9E0",
    "text": "#14171C",
    "text_secondary": "#3A404C",
    "text_muted": "#5B6372",
    "text_faint": "#8A92A0",
    "accent": "#0B7D72",
    "accent_strong": "#0B7D72",
    "accent_soft": "#DDF3F0",
    "accent_on": "#FFFFFF",
    "accent_text": "#075E56",
    "warn": "#D98A0B",
    "warn_soft": "#FDF0DC",
    "warn_text": "#7A4A06",
    "danger": "#DC2626",
    "danger_soft": "#FDECEC",
    "danger_border": "#F1B5B5",
    "danger_text": "#A61B1B",
    "video_bg": "#0A0C10",
    "console_bg": "#14171C",
    "series_1": "#C2570C",
    "series_2": "#2563EB",
    "series_3": "#7C3AED",
    "series_4": "#A16207",
}

FONT_UI = "'Inter', 'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Mono', Consolas, 'DejaVu Sans Mono', monospace"


def get_theme(dark: bool) -> dict:
    return DARK if dark else LIGHT


def build_stylesheet(t: dict) -> str:
    """Folha de estilo global do app para a paleta ``t``."""
    return f"""
    * {{ font-family: {FONT_UI}; }}
    QMainWindow, QWidget#root, QStackedWidget, QWidget#page {{ background: {t['bg']}; }}
    QWidget {{ color: {t['text']}; font-size: 13px; }}
    QLabel {{ background: transparent; }}
    QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']}; padding: 6px 8px; border-radius: 6px; }}

    /* ── Cabeçalho ─────────────────────────────────────────── */
    QFrame#header {{ background: {t['header_bg']}; border: none; border-bottom: 1px solid {t['border']}; }}
    QFrame#logo_badge {{ background: {t['accent_soft']}; border-radius: 9px; }}
    QLabel#app_name {{ font-size: 15px; font-weight: 600; color: {t['text']}; }}
    QLabel#app_tagline {{ font-size: 11px; color: {t['text_muted']}; }}

    /* ── Tipografia ────────────────────────────────────────── */
    QLabel#h1 {{ font-size: 18px; font-weight: 600; color: {t['text']}; }}
    QLabel#h2 {{ font-size: 14px; font-weight: 600; color: {t['text']}; }}
    QLabel#caption, QLabel[role="muted"] {{ font-size: 12px; color: {t['text_muted']}; }}
    QLabel#eyebrow {{ font-size: 12px; font-weight: 500; color: {t['text_muted']}; }}
    QLabel#display {{ font-size: 28px; font-weight: 700; color: {t['text']}; }}
    QLabel#metric {{ font-family: {FONT_MONO}; font-size: 15px; font-weight: 600; color: {t['accent_strong']}; }}
    QLabel[role="mono"] {{ font-family: {FONT_MONO}; font-size: 13px; color: {t['text']}; }}
    QLabel[role="mono_muted"] {{ font-family: {FONT_MONO}; font-size: 12px; color: {t['text_muted']}; }}
    QLabel[role="finger"] {{ font-size: 13px; color: {t['text_secondary']}; }}
    QLabel#empty_title {{ font-size: 16px; font-weight: 600; color: {t['text']}; }}

    /* ── Cartões ───────────────────────────────────────────── */
    QFrame[card="true"] {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 16px; }}
    QFrame[card="true"] QLabel {{ background: transparent; }}
    QFrame#video_frame {{ background: {t['video_bg']}; border: 1px solid {t['border']}; border-radius: 16px; }}
    QLabel#video {{ background: {t['video_bg']}; color: #9AA3B2; font-size: 13px; border-radius: 12px; }}
    QLabel#overlay_chip {{ background: rgba(15,17,21,0.78); color: #E7E9EE; font-size: 12px; padding: 4px 10px; border-radius: 7px; }}
    QFrame#divider {{ background: {t['border']}; border: none; max-height: 1px; min-height: 1px; }}
    QLabel#gesture_img {{ background: {t['surface_alt']}; border: none; border-radius: 12px; color: {t['text_muted']}; font-size: 11px; }}

    /* ── Barra de status ───────────────────────────────────── */
    QFrame#statusbar {{ background: {t['header_bg']}; border: none; border-top: 1px solid {t['border']}; }}
    QLabel#status_text {{ font-family: {FONT_MONO}; font-size: 12px; color: {t['text_muted']}; }}

    /* ── Chips de status ───────────────────────────────────── */
    QLabel[chip="true"] {{ font-size: 12px; font-weight: 500; padding: 5px 10px; border-radius: 8px; }}
    QLabel[chip="true"][level="ok"] {{ background: {t['accent_soft']}; color: {t['accent_text']}; }}
    QLabel[chip="true"][level="warn"] {{ background: {t['warn_soft']}; color: {t['warn_text']}; }}
    QLabel[chip="true"][level="danger"] {{ background: {t['danger_soft']}; color: {t['danger_text']}; }}
    QLabel[chip="true"][level="off"] {{ background: {t['surface_alt']}; color: {t['text_muted']}; }}
    QLabel[chip="true"][level="mono"] {{ background: {t['surface_alt']}; color: {t['text_secondary']}; font-family: {FONT_MONO}; }}

    /* ── Controles segmentados ─────────────────────────────── */
    QFrame[segmented="true"] {{ background: {t['surface_alt']}; border: 1px solid {t['border']}; border-radius: 11px; }}
    QPushButton[seg="true"] {{
        background: transparent; color: {t['text_muted']}; border: none; border-radius: 8px;
        padding: 0 14px; min-height: 32px; font-size: 13px; font-weight: 500;
    }}
    QPushButton[seg="true"]:hover {{ color: {t['text']}; }}
    QPushButton[seg="true"]:checked {{ background: {t['raised']}; color: {t['text']}; font-weight: 600; }}
    QPushButton[seg="true"][size="sm"] {{ min-height: 28px; padding: 0 12px; font-size: 12px; }}
    QPushButton[seg="true"][accent="true"]:checked {{ background: {t['accent']}; color: {t['accent_on']}; }}

    /* ── Botões ────────────────────────────────────────────── */
    QPushButton {{
        background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']};
        border-radius: 10px; padding: 0 14px; min-height: 36px; font-size: 13px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {t['surface_alt']}; }}
    QPushButton:disabled {{ color: {t['text_faint']}; border-color: {t['border']}; }}
    QPushButton[variant="primary"] {{ background: {t['accent']}; color: {t['accent_on']}; border: none; }}
    QPushButton[variant="primary"]:hover {{ background: {t['accent_strong']}; }}
    QPushButton[variant="primary"]:disabled {{ background: {t['track']}; color: {t['text_faint']}; }}
    QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid {t['border']}; color: {t['text_secondary']}; font-weight: 500; }}
    QPushButton[variant="ghost"]:hover {{ background: {t['surface_alt']}; color: {t['text']}; }}
    QPushButton[variant="icon"] {{ background: transparent; border: 1px solid {t['border']}; min-height: 0; padding: 0; border-radius: 9px; }}
    QPushButton[variant="icon"]:hover {{ background: {t['surface_alt']}; }}
    QPushButton[variant="icon"]:checked {{ background: {t['raised']}; border-color: {t['border_strong']}; }}
    QPushButton#console_btn {{ min-height: 26px; max-height: 26px; padding: 0 10px; font-size: 12px; font-weight: 500; }}
    QPushButton#stop_button {{
        background: {t['danger_soft']}; color: {t['danger_text']}; border: 1px solid {t['danger_border']};
        border-radius: 14px; min-height: 52px; font-size: 14px; font-weight: 600;
    }}
    QPushButton#stop_button:hover {{ border: 1px solid {t['danger']}; }}
    QPushButton#stop_button:pressed {{ background: {t['danger_border']}; }}

    /* ── Barras de progresso ───────────────────────────────── */
    QProgressBar {{ background: {t['track']}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
    QProgressBar::chunk {{ background: {t['accent']}; border-radius: 3px; }}
    QProgressBar[size="lg"] {{ border-radius: 5px; max-height: 10px; min-height: 10px; }}
    QProgressBar[size="lg"]::chunk {{ border-radius: 5px; }}
    QProgressBar[series="1"]::chunk {{ background: {t['series_1']}; }}
    QProgressBar[series="2"]::chunk {{ background: {t['series_2']}; }}
    QProgressBar[series="3"]::chunk {{ background: {t['series_3']}; }}
    QProgressBar[series="4"]::chunk {{ background: {t['series_4']}; }}

    /* ── Campos ────────────────────────────────────────────── */
    QComboBox, QDoubleSpinBox {{
        background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']};
        border-radius: 8px; padding: 0 10px; min-height: 34px; font-size: 13px;
    }}
    QDoubleSpinBox {{ font-family: {FONT_MONO}; padding-right: 4px; }}
    QComboBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {t['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border_strong']};
        selection-background-color: {t['accent_soft']}; selection-color: {t['text']}; outline: none; padding: 4px;
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 16px; border: none; background: transparent; }}
    QLabel[role="field"] {{ font-size: 12px; font-weight: 500; color: {t['text_muted']}; }}

    QTextEdit#console {{
        background: {t['console_bg']}; color: #C9CED8; border: 1px solid {t['border']};
        border-radius: 12px; padding: 10px; font-family: {FONT_MONO}; font-size: 12px;
    }}

    /* ── Rolagem ───────────────────────────────────────────── */
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; margin: 2px; }}
    QScrollBar:horizontal {{ height: 10px; background: transparent; margin: 2px; }}
    QScrollBar::handle {{ background: {t['border_strong']}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
    QScrollBar::handle:hover {{ background: {t['text_faint']}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; width: 0; height: 0; }}
    """


def repolish(widget):
    """Reaplica o estilo depois de mudar uma propriedade dinâmica."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
