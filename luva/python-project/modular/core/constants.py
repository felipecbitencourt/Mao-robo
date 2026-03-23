"""
constants.py
Constantes e configurações globais do sistema de neuroreabilitação
Versão 2.0 - Com suporte ao driver 5DT no Windows (USB0)
"""

import os
import platform
import logging
from pathlib import Path

# Configurar logger
logger = logging.getLogger('Constants')

# ============================================================
# PATHS E ARQUIVOS
# ============================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(ROOT_DIR)  # Pasta acima de 'core'
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMAGES_FOLDER = os.path.join(ASSETS_DIR, "gesture-images")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Criar diretórios se não existirem
for directory in [ASSETS_DIR, DATA_DIR, LOG_DIR, IMAGES_FOLDER]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Caminho para o executável do driver
PATH_TO_C_EXE = os.path.join(BASE_DIR, "TestGlove64.exe")

# Verificar caminhos alternativos se não encontrar
if not os.path.exists(PATH_TO_C_EXE):
    alternative_paths = [
        "./TestGlove64.exe",
        "../TestGlove64.exe",
        "TestGlove64.exe",
        os.path.join(os.getcwd(), "TestGlove64.exe")
    ]
    
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            PATH_TO_C_EXE = os.path.abspath(alt_path)
            logger.info(f"Executável encontrado em: {PATH_TO_C_EXE}")
            break
    else:
        logger.warning(f"⚠️ Executável não encontrado em nenhum caminho padrão")

# ============================================================
# DETECÇÃO AUTOMÁTICA DE PORTA (IGNORADA NO WINDOWS)
# ============================================================
def detect_glove_port(preferred_port=None):
    """
    Detecta automaticamente a porta COM.
    - NÃO funciona para 5DT no Windows (porta USB0 não aparece).
    Usado apenas no Linux.
    """
    system = platform.system()
    
    if preferred_port:
        logger.info(f"Usando porta especificada: {preferred_port}")
        return preferred_port
    
    try:
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        
        if not ports:
            logger.warning("Nenhuma porta COM detectada")
            default = "/dev/ttyUSB0"
            logger.info(f"Usando porta padrão: {default}")
            return default
        
        logger.info(f"Portas disponíveis ({len(ports)}):")
        for port in ports:
            logger.info(f"  • {port.device}: {port.description}")
        
        priority_keywords = ['5dt', 'glove']
        usb_keywords = ['usb', 'serial', 'ftdi', 'ch340', 'cp210', 'prolific']
        
        candidates = []
        
        for port in ports:
            combined = f"{port.description.lower()} {port.hwid.lower()}"
            score = 0
            for kw in priority_keywords:
                if kw in combined:
                    score += 10
            for kw in usb_keywords:
                if kw in combined:
                    score += 1
            
            if score > 0:
                candidates.append((score, port.device, port.description))
        
        candidates.sort(reverse=True)
        
        if candidates:
            return candidates[0][1]
        
        return ports[0].device
        
    except Exception:
        return "/dev/ttyUSB0"

# ============================================================
# PORTAS — CORREÇÃO IMPORTANTE
# ============================================================

# A 5DT Data Glove usa **USB0** no Windows (driver oficial)
if platform.system() == "Windows":
    _DEFAULT_PORT = "USB0"
    GLOVE_CONNECTION_PORT = _DEFAULT_PORT
else:
    _DEFAULT_PORT = "/dev/ttyUSB0"
    GLOVE_CONNECTION_PORT = detect_glove_port()

    
# Configurações de comunicação serial (não usadas pela 5DT,
# mas deixadas para compatibilidade)

# Detectar porta automaticamente ou usar padrão
# Para forçar uma porta específica, passe como argumento:
# GLOVE_CONNECTION_PORT = detect_glove_port("COM4")
GLOVE_CONNECTION_PORT = "USB0"


BAUD_RATE = 115200
SERIAL_TIMEOUT = 0.05

# Intervalo de reconexão automática
RECONNECT_INTERVAL = 2.0
MAX_RECONNECT_ATTEMPTS = 5

# ============================================================
# SENSOR CONFIG
# ============================================================

SENSOR_NAMES = [
    "Thumb Near", "Thumb Far", "Thumb/Index",
    "Index Near", "Index Far", "Index/Middle",
    "Middle Near", "Middle Far", "Middle/Ring",
    "Ring Near", "Ring Far", "Ring/Little",
    "Little Near", "Little Far",
    "Thumb Palm", "Wrist Bend", "Roll", "Pitch"
]

NUM_SENSORS = len(SENSOR_NAMES)
DEFAULT_SAMPLE_RATE_HZ = 60

# ============================================================
# CALIBRAÇÃO
# ============================================================

DEFAULT_CALIBRATION_CYCLES = 10
DEFAULT_CYCLE_DURATION = 5.0
DEFAULT_CONTINUOUS_MODE = False

CALIBRATION_OPEN_TIME = 5
CALIBRATION_CLOSE_TIME = 5
CALIBRATION_REST_TIME = 1

CALIBRATION_MODES = {
    "continuous": 0,
    "cycle": 1,
    "manual": 2
}

MIN_CALIBRATION_CYCLES = 3
MAX_CALIBRATION_CYCLES = 50

# ============================================================
# PROCESSAMENTO DE DADOS
# ============================================================

ARTIFACT_WINDOW_SIZE = 5
ARTIFACT_THRESHOLD = 0.15
SMOOTHING_ENABLED = True
SMOOTHING_ALPHA = 0.3

SENSOR_MIN_VALUE = 0.0
SENSOR_MAX_VALUE = 1.0

# ============================================================
# LED COLORS / UI
# ============================================================

LED_COLORS = {
    "connected": "#10b981",
    "disconnected": "#ef4444",
    "reading": "#f59e0b",
    "calibrating": "#3b82f6",
    "error": "#dc2626",
    "idle": "#6b7280"
}

COLORS = {
    'primary': '#3b82f6',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'background': '#f0f4f8',
    'card': '#ffffff',
    'text_primary': '#1a202c',
    'text_secondary': '#4a5568',
    'border': '#e5e7eb'
}

# ============================================================
# IMAGENS
# ============================================================

IMAGE_MAP = {i: f"{i}.png" for i in range(16)}
IMAGE_MAP[-1] = "unknown.png"

DEFAULT_IMAGE_SIZE = (400, 400)

# ============================================================
# UI
# ============================================================

WINDOW_SCREEN_RATIO = 0.90
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 600
UI_UPDATE_INTERVAL_STATUS = 200
UI_UPDATE_INTERVAL_DATA = 20

# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = logging.INFO
LOG_FILE = os.path.join(LOG_DIR, "glove_app.log")
LOG_FORMAT = "%(asctime)s [%(name)s][%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_SIZE = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# ============================================================
# DATABASE
# ============================================================

DB_FILE = os.path.join(DATA_DIR, "sessions.db")
MAX_HISTORY_SESSIONS = 100

# ============================================================
# APLICAÇÃO
# ============================================================

APP_NAME = "Sistema de Neuroreabilitação"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Brain Glove Team"
APP_DESCRIPTION = "Sistema de reabilitação com Luva 5DT Data Glove"

# ============================================================
# VALIDAÇÃO
# ============================================================

def validate_configuration():
    warnings = []
    errors = []
    is_valid = True
    
    if not os.path.exists(PATH_TO_C_EXE):
        errors.append(f"❌ Executável não encontrado: {PATH_TO_C_EXE}")
        is_valid = False
    
    try:
        import serial
    except ImportError:
        warnings.append("⚠️ Biblioteca pyserial não instalada (não é usada no Windows)")
    
    if not GLOVE_CONNECTION_PORT:
        errors.append("❌ Porta da luva não definida")
        is_valid = False
    
    return is_valid, warnings, errors

# Auto-validação
if __name__ != "__main__":
    is_valid, warnings, errors = validate_configuration()
    for w in warnings:
        logger.warning(w)
    for e in errors:
        logger.error(e)
