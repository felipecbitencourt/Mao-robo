# core/data_processing.py
import numpy as np
from collections import deque


class DataProcessor:
    """
    Classe de processamento de dados da luva:
        - Filtro de média móvel
        - Cálculos básicos: min, max, amplitude, média
        - FFT para frequência dominante
        - Parsing seguro dos pacotes vindos do glove_thread

    Compatível com:
        - frequency_plot.py (FFT)
        - vector_viewer.py (amplitude / média / vetores por sensor)
    """

    def __init__(self, sensor_count, filter_window=5):
        self.sensor_count = sensor_count
        self.filter_window = filter_window

        # Histórico para filtros e FFT
        self.buffers = [deque(maxlen=filter_window) for _ in range(sensor_count)]
        self.fft_buffers = [deque(maxlen=256) for _ in range(sensor_count)]  # janela para FFT

    # ================================================================
    # PARSE DE PACOTE BRUTO
    # ================================================================
    def parse_packet(self, packet_str, sensor_names):
        """
        Formato esperado:
            GID, s0, s1, ..., sN
        GID = ID do gesto detectado pelo algoritmo C (0-15)
        """
        data_list = packet_str.split(",")

        if len(data_list) != len(sensor_names) + 1:
            return None, None

        try:
            gesture_id = int(data_list[0])
            sensor_values = [float(v) for v in data_list[1:]]
            return gesture_id, sensor_values
        except Exception:
            return None, None

    # ================================================================
    # FILTRO DE RUÍDO (MÉDIA MÓVEL)
    # ================================================================
    def smooth(self, values):
        """
        Retorna valores suavizados sensor a sensor usando média móvel.
        """
        smoothed = []
        for i, val in enumerate(values):
            self.buffers[i].append(val)
            smoothed.append(sum(self.buffers[i]) / len(self.buffers[i]))
        return smoothed

    # ================================================================
    # CÁLCULOS SIMPLES
    # ================================================================
    @staticmethod
    def calc_min(values):
        return float(min(values))

    @staticmethod
    def calc_max(values):
        return float(max(values))

    @staticmethod
    def calc_mean(values):
        return float(sum(values) / len(values)) if values else 0.0

    @staticmethod
    def calc_amplitude(values):
        return float(max(values) - min(values))

    # ================================================================
    # FFT E FREQUÊNCIA DOMINANTE
    # ================================================================
    def update_fft_buffer(self, sensor_values):
        """
        Mantém janelas de 256 amostras para cada sensor.
        Deve ser chamado a cada leitura.
        """
        for i, val in enumerate(sensor_values):
            self.fft_buffers[i].append(val)

    def dominant_frequency(self, sensor_index, sampling_rate):
        """
        Retorna frequência dominante de um sensor específico.
        Compatível com frequency_plot.py.
        """
        buf = self.fft_buffers[sensor_index]
        if len(buf) < 32:
            return 0.0  # não há dados suficientes

        signal = np.array(buf)
        fft_vals = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / sampling_rate)

        # Ignorar componente DC (freq = 0)
        if len(fft_vals) > 1:
            fft_vals[0] = 0

        dominant_idx = np.argmax(fft_vals)
        return float(freqs[dominant_idx])

    def dominant_frequencies_all(self, sampling_rate):
        """
        Retorna lista com frequência dominante de todos sensores.
        """
        return [
            self.dominant_frequency(i, sampling_rate)
            for i in range(self.sensor_count)
        ]
# ================================================================
# EXTRAÇÃO DE ESTADO DO GESTO (API usada por feedback_screen)
# ================================================================
def extract_gesture_state(gesture_id, sensor_values, threshold=0.7):
    """
    Converte o gesture_id e/ou valores dos sensores em um estado textual
    para a interface gráfica.

    Compatível com feedback_screen.py.

    Regras:
      - Se gesture_id for válido (0–15), retorna um nome de gesto.
      - Caso contrário, usa thresholds para definir estado da mão.
    """

    GESTURE_NAMES = {
        0: "RELAX",
        1: "PINCH",
        2: "FIST",
        3: "POINT",
        4: "GRAB",
        5: "SPREAD",
        6: "SHAKE",
        7: "SWIPE LEFT",
        8: "SWIPE RIGHT",
        9: "CIRCLE",
        # pode expandir até 15...
    }

    # Caso o firmware já tenha detectado o gesto
    if gesture_id in GESTURE_NAMES:
        return GESTURE_NAMES[gesture_id]

    # fallback → calcular baseado apenas nos sensores
    max_val = max(sensor_values)

    if max_val > threshold:
        return "ACTIVE"
    else:
        return "RELAX"
# ================================================================
# COMPUTE VECTOR (API para VectorViewer)
# ================================================================
def compute_vector(sensor_values, mode="2d"):
    """
    Converte valores dos sensores em um vetor 2D ou 3D.
    Compatível com VectorViewer.
    """

    if not sensor_values:
        return (0, 0) if mode == "2d" else (0, 0, 0)

    # Divisão simples em dois grupos (ajustável conforme sua luva)
    half = len(sensor_values) // 2
    group_A = sensor_values[:half]
    group_B = sensor_values[half:]

    x = sum(group_A) / len(group_A)
    y = sum(group_B) / len(group_B)

    if mode == "2d":
        return x, y

    # modo 3D → usar amplitude como Z
    z = max(sensor_values) - min(sensor_values)
    return x, y, z
# ================================================================
# COMPUTE FREQUENCY (API para FrequencyPlot)
# ================================================================
def compute_frequency(processor, sensor_values, sampling_rate=50):
    """
    Wrapper procedural usado por feedback_screen.py.
    Atualiza buffers e retorna lista de frequências dominantes.
    """
    processor.update_fft_buffer(sensor_values)
    return processor.dominant_frequencies_all(sampling_rate)
