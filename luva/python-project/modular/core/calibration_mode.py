# core/calibration_mode.py

import time


class CalibrationMode:
    """
    Controla o processo de calibração da luva.
    Independente da interface gráfica.

    Funciona em dois modos:
        - continuous: min/max globais
        - cycles: min/max por ciclos sucessivos

    Permite:
        - selecionar sensores
        - configurar duração dos ciclos
        - callbacks para integração com a UI
    """

    def __init__(self, sensor_names):
        self.sensor_names = sensor_names
        self.sensor_count = len(sensor_names)

        # Configurações
        self.mode = "cycles"
        self.disabled_mask = [False] * self.sensor_count
        self.num_cycles = 10
        self.cycle_duration = 4.0  # segundos

        # Callbacks (GUI registra aqui)
        self.on_cycle_start = None
        self.on_cycle_progress = None
        self.on_cycle_end = None
        self.on_continuous_update = None
        self.on_finish = None

        self.reset()

    # --------------------------------------------------
    # Reset total
    # --------------------------------------------------
    def reset(self):
        """Limpa todo o estado interno da calibração."""
        self.current_cycle = 0
        self.cycle_start_time = None
        self.running = False

        # Dados contínuos
        self.global_min = [1.0] * self.sensor_count
        self.global_max = [0.0] * self.sensor_count

        # Dados por ciclo
        self.current_min = None
        self.current_max = None
        self.cycles_min = []
        self.cycles_max = []

    # --------------------------------------------------
    # Configurações
    # --------------------------------------------------
    def set_mode(self, mode):
        assert mode in ("continuous", "cycles")
        self.mode = mode

    def set_cycle_parameters(self, num_cycles, cycle_duration):
        self.num_cycles = num_cycles
        self.cycle_duration = cycle_duration

    def set_disabled_sensors(self, disabled_mask):
        self.disabled_mask = disabled_mask

    # --------------------------------------------------
    # Controle de execução
    # --------------------------------------------------
    def start(self):
        """Inicia o processo de calibração."""
        self.reset()
        self.running = True

        if self.mode == "cycles":
            self.start_cycle()

    def stop(self):
        """Interrompe imediatamente a calibração."""
        self.running = False

    # --------------------------------------------------
    # MODO POR CICLOS
    # --------------------------------------------------
    def start_cycle(self):
        """Inicia um novo ciclo."""
        self.current_cycle += 1
        self.cycle_start_time = time.time()

        self.current_min = [1.0] * self.sensor_count
        self.current_max = [0.0] * self.sensor_count

        if self.on_cycle_start:
            self.on_cycle_start(self.current_cycle)

    def cycle_active(self):
        """Retorna True se o ciclo ainda está dentro do tempo."""
        if not self.running:
            return False
        if self.cycle_start_time is None:
            return False

        elapsed = time.time() - self.cycle_start_time

        # Callback para progresso (0.0 a 1.0)
        if self.on_cycle_progress:
            self.on_cycle_progress(min(elapsed / self.cycle_duration, 1.0))

        return elapsed < self.cycle_duration

    def finish_cycle(self):
        """Finaliza um ciclo e salva valores."""
        self.cycles_min.append(self.current_min[:])
        self.cycles_max.append(self.current_max[:])

        if self.on_cycle_end:
            self.on_cycle_end(self.current_cycle)

    # --------------------------------------------------
    # ATUALIZAÇÃO DOS DADOS
    # --------------------------------------------------
    def update(self, sensor_values):
        """
        Atualiza a calibração com leituras da luva.
        Chamado continuamente pelo app.
        """

        if not self.running:
            return

        if self.mode == "continuous":
            self._update_continuous(sensor_values)
        else:
            self._update_cycle(sensor_values)

    # --- Atualização por ciclo ---
    def _update_cycle(self, values):
        if not self.cycle_active():
            # O ciclo encerrou
            self.finish_cycle()

            if self.current_cycle < self.num_cycles:
                self.start_cycle()
            else:
                self.running = False
                self._finish_calibration()
            return

        # Coleta min/max do ciclo atual
        for i, val in enumerate(values):
            if self.disabled_mask[i]:
                continue

            if val < self.current_min[i]:
                self.current_min[i] = val
            if val > self.current_max[i]:
                self.current_max[i] = val

    # --- Atualização contínua ---
    def _update_continuous(self, values):
        for i, val in enumerate(values):
            if self.disabled_mask[i]:
                continue

            if val < self.global_min[i]:
                self.global_min[i] = val
            if val > self.global_max[i]:
                self.global_max[i] = val

        if self.on_continuous_update:
            self.on_continuous_update(self.global_min, self.global_max)

    # --------------------------------------------------
    # FINALIZAÇÃO
    # --------------------------------------------------
    def _finish_calibration(self):
        """Processa os valores finais e dispara callback."""
        results = self.compute_results()

        if self.on_finish:
            self.on_finish(results)

    def compute_results(self):
        """Gera min, max e thresholds ajustados."""
        if self.mode == "continuous":
            mins = self.global_min
            maxs = self.global_max

        else:
            # Médias entre ciclos
            num = len(self.cycles_min)
            mins = [
                sum(c[i] for c in self.cycles_min) / num
                for i in range(self.sensor_count)
            ]
            maxs = [
                sum(c[i] for c in self.cycles_max) / num
                for i in range(self.sensor_count)
            ]

        thresholds = [
            (mn + mx) / 2 for mn, mx in zip(mins, maxs)
        ]

        return {
            "mode": self.mode,
            "num_cycles": self.num_cycles,
            "cycle_duration": self.cycle_duration,
            "sensor_min": mins,
            "sensor_max": maxs,
            "sensor_threshold": thresholds,
            "disabled_sensors": self.disabled_mask,
            "raw_cycles_min": self.cycles_min,
            "raw_cycles_max": self.cycles_max
        }
