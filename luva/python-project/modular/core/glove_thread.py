"""
glove_thread.py - Versão híbrida com diagnóstico completo da porta
Compatível com TestGlove64.exe, com reconexão e logs detalhados.
"""

import subprocess
import threading
import queue
import time
import os
import logging
import re

DEFAULT_SAMPLING_RATE = 60
RECONNECT_DELAY = 2

logger = logging.getLogger("GloveReaderThread")


class GloveReaderThread(threading.Thread):
    """
    Thread confiável para leitura da luva FiveDT.
    Agora com diagnóstico completo da porta e teste rápido do executável.
    """

    def __init__(
        self,
        output_queue: queue.Queue,
        status_queue: queue.Queue,
        c_exe_path: str,
        glove_port: str,
        sampling_rate: int = DEFAULT_SAMPLING_RATE,
        debug: bool = False,
        auto_reconnect: bool = True,
    ):
        super().__init__(daemon=True)

        self.output_queue = output_queue
        self.status_queue = status_queue
        self.c_exe_path = c_exe_path
        self.glove_port = glove_port
        self.sampling_rate = sampling_rate
        self.auto_reconnect = auto_reconnect

        self._stop_event = threading.Event()
        self._process = None
        self._last_status = None

        # LOG
        log_level = logging.DEBUG if debug else logging.INFO
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[GloveThread][%(levelname)s] %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(log_level)

        logger.info(f"Thread inicializada: porta={glove_port}, auto_reconnect={auto_reconnect}")

    # =====================================================================
    # TESTE RÁPIDO DO EXECUTÁVEL ANTES DA CONEXÃO REAL
    # =====================================================================
    def _test_port_before_run(self):
        """
        Executa o TestGlove64 por 1 segundo para verificar se a porta abre.
        """
        print("[GloveThread] Testando porta antes da conexão real…")

        try:
            res = subprocess.run(
                [self.c_exe_path, self.glove_port],
                capture_output=True,
                text=True,
                timeout=1
            )
        except subprocess.TimeoutExpired:
            print("[INFO] Timeout esperado. O executável provavelmente abriu e está aguardando.")
            return True

        # Print detalhado
        print("\n[TESTE - STDOUT]")
        print(res.stdout.strip())
        print("\n[TESTE - STDERR]")
        print(res.stderr.strip())

        # Avaliar erro conhecido
        if "falhou" in res.stdout.lower() or "error" in res.stdout.lower():
            print("\n[ERRO] O executável NÃO conseguiu abrir esta porta!")
            print("Conexão será cancelada.\n")
            return False

        return True

    # =====================================================================
    # EXECUÇÃO PRINCIPAL
    # =====================================================================
    def run(self):
        logger.info("Thread iniciada")

        # Teste inicial — IMPORTANTÍSSIMO
        if not self._test_port_before_run():
            self._update_status("error_port_invalid")
            return

        while not self._stop_event.is_set():

            if not os.path.exists(self.c_exe_path):
                logger.error(f"Executável não encontrado: {self.c_exe_path}")
                self._update_status("error_executable_not_found")
                break

            self._update_status("connecting")

            try:
                logger.debug(f"Iniciando: {self.c_exe_path} {self.glove_port}")

                self._process = subprocess.Popen(
                    [self.c_exe_path, self.glove_port],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                logger.info(f"Processo iniciado (PID: {self._process.pid})")
                self._update_status("connected")

                self._simple_read_loop()

            except Exception as e:
                logger.error(f"Erro no loop principal: {e}", exc_info=True)
                self._update_status(f"error_{type(e).__name__}")

            finally:
                self._terminate_process()
                self._update_status("disconnected")

                if not self._stop_event.is_set() and self.auto_reconnect:
                    logger.info(f"Aguardando {RECONNECT_DELAY}s antes de reconectar…")
                    time.sleep(RECONNECT_DELAY)
                else:
                    break

        logger.info("Thread finalizada")

    # =====================================================================
    def _simple_read_loop(self):
        while not self._stop_event.is_set():
            try:
                line = self._process.stdout.readline()

                if not line:
                    logger.warning("Processo terminou (stdout fechado)")
                    stderr_output = self._drain_stderr()

                    if stderr_output:
                        logger.error(f"Erro do processo:\n{stderr_output}")

                    break

                clean = line.strip()
                if clean:
                    logger.debug(f"Recebido: {clean}")
                    self.output_queue.put(clean)

            except Exception as e:
                logger.error(f"Erro lendo stdout: {e}")
                break

    # =====================================================================
    def _drain_stderr(self):
        if not self._process or not self._process.stderr:
            return ""
        try:
            lines = []
            while True:
                line = self._process.stderr.readline()
                if not line:
                    break
                lines.append(line.rstrip())
            return "\n".join(lines)
        except:
            return ""

    # =====================================================================
    def _update_status(self, new_status: str):
        if new_status != self._last_status:
            logger.info(f"Status: {self._last_status} -> {new_status}")
            self.status_queue.put(new_status)
            self._last_status = new_status

    # =====================================================================
    def _terminate_process(self):
        if not self._process:
            return
        try:
            if self._process.poll() is None:
                logger.debug("Finalizando processo…")
                self._process.terminate()
                try:
                    self._process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("Processo travado — forçando kill")
                    self._process.kill()
                    self._process.wait()
        except:
            pass
        self._process = None

    # =====================================================================
    def stop(self):
        logger.info("Comando de parada recebido")
        self._stop_event.set()
        self._terminate_process()
        self._update_status("stopped")

    def is_running(self):
        return not self._stop_event.is_set()


logger.info("Módulo glove_thread carregado com diagnóstico avançado")