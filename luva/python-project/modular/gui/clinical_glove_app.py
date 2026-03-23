"""
clinical_glove_app.py
Controlador principal da aplicação - Versão Corrigida e Otimizada

Responsabilidades:
    • Inicializar e gerenciar a thread da luva
    • Gerenciar navegação entre telas
    • Processar dados em tempo real
    • Atualizar status de conexão
    • Tratamento robusto de erros
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox
import logging
import os
from PIL import Image, ImageTk

# Core
from core.glove_thread import GloveReaderThread
from core.constants import PATH_TO_C_EXE, GLOVE_CONNECTION_PORT, SENSOR_NAMES
from core.state_manager import StateManager
from core.data_processing import DataProcessor

# Screens
from gui.screens.main_screen import MainScreen
from gui.screens.calibration_screen import CalibrationScreen
from gui.screens.results_screen import ResultsScreen
from gui.screens.feedback_screen import FeedbackScreen
from gui.screens.history_screen import HistoryScreen

# Configurar logging
logger = logging.getLogger('ClinicalGloveApp')


class ClinicalGloveApp:
    """
    Controlador principal da aplicação de neuroreabilitação com luva 5DT.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistema de Neuroreabilitação - Luva 5DT")
        self.root.configure(bg="#f0f4f8")
        
        # Configurar tamanho da janela
        self._setup_window_size()

        # Estado da aplicação
        self.state = StateManager()
        self.glove_connected = False
        self._connection_attempts = 0
        self._max_connection_attempts = 3

        # Filas de comunicação com a thread da luva
        self.data_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.glove_thread = None  # ✅ Nome consistente
        self._thread_lock = threading.Lock()  # ✅ Thread-safe

        # Processador de dados (filtro, parsing, etc.)
        self.processor = DataProcessor(sensor_count=len(SENSOR_NAMES))

        # Número de sensores (usado pelas telas que constroem SensorList)
        self.num_sensors = len(SENSOR_NAMES)
        
        # Dados de calibração iniciais (usado pelas telas)
        self.calibration_data = {
            "sensor_min": [0.0] * self.num_sensors,
            "sensor_max": [0.0] * self.num_sensors,
            "sensor_threshold": [0.5] * self.num_sensors
        }

        # Carregar imagens de gesto UMA VEZ e compartilhar com as telas
        self.gesture_images = {}
        try:
            imgs_dir = os.path.join(os.getcwd(), "assets", "gesture-images")
            if os.path.isdir(imgs_dir):
                for fname in sorted(os.listdir(imgs_dir)):
                    base, ext = os.path.splitext(fname)
                    try:
                        key = int(base)
                    except Exception:
                        continue
                    path = os.path.join(imgs_dir, fname)
                    try:
                        img = Image.open(path).resize((320, 320), Image.Resampling.LANCZOS)
                        self.gesture_images[key] = ImageTk.PhotoImage(img)
                    except Exception:
                        logger.exception("Falha ao carregar imagem %s", path)
        except Exception:
            logger.exception("Erro ao iniciar carregamento de imagens de gesto")

        # Tela ativa
        self.active_screen = None
        
        # Flags de controle
        self._is_closing = False
        self._updates_running = False

        # Carrega tela inicial
        self.show_main_screen()

        # Inicia comunicação com a luva
        self.start_connection()

        # Atualizações periódicas
        self._start_periodic_updates()

        # Fechamento limpo
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        logger.info("Aplicação inicializada com sucesso")
        print("PORT DETECTADA:", GLOVE_CONNECTION_PORT)


    # ============================================================
    # CONFIGURAÇÃO INICIAL
    # ============================================================
    def _setup_window_size(self):
        """Configura tamanho da janela baseado na resolução da tela"""
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # 90% da tela
        app_w = int(screen_w * 0.90)
        app_h = int(screen_h * 0.90)
        
        # Centralizar
        x = (screen_w - app_w) // 2
        y = (screen_h - app_h) // 2
        
        self.root.geometry(f"{app_w}x{app_h}+{x}+{y}")
        self.root.minsize(900, 600)  # Tamanho mínimo
        self.root.resizable(True, True)

    # ============================================================
    # GESTÃO DE TELAS
    # ============================================================
    def clear_screen(self):
        """Remove todos os widgets da janela"""
        for widget in self.root.winfo_children():
            widget.destroy()
        self.active_screen = None

    def show_main_screen(self):
        """Exibe a tela principal"""
        self.clear_screen()
        self.state.set_screen("main")
        try:
            self.active_screen = MainScreen(master=self.root, app=self)
            logger.info("Tela principal carregada")
        except Exception as e:
            logger.error(f"Erro ao carregar tela principal: {e}", exc_info=True)
            self._show_error("Erro ao carregar interface", str(e))

    def show_calibration_screen(self):
        """Exibe a tela de calibração"""
        if not self.glove_connected:
            messagebox.showwarning(
                "Luva Desconectada",
                "Conecte a luva antes de iniciar a calibração."
            )
            return
        
        self.clear_screen()
        self.state.set_screen("calibration")
        try:
            self.active_screen = CalibrationScreen(master=self.root, app=self)
            logger.info("Tela de calibração carregada")
        except Exception as e:
            logger.error(f"Erro ao carregar tela de calibração: {e}", exc_info=True)
            self._show_error("Erro ao carregar calibração", str(e))
            self.show_main_screen()

    def show_results_screen(self, results):
        """Exibe a tela de resultados da calibração"""
        self.clear_screen()
        self.state.set_screen("results")
        try:
            self.active_screen = ResultsScreen(
                master=self.root, 
                app=self, 
                results_data=results
            )
            logger.info("Tela de resultados carregada")
        except Exception as e:
            logger.error(f"Erro ao carregar tela de resultados: {e}", exc_info=True)
            self._show_error("Erro ao carregar resultados", str(e))
            self.show_main_screen()

    def show_feedback_screen(self):
        """Exibe a tela de feedback em tempo real"""
        if not self.glove_connected:
            messagebox.showwarning(
                "Luva Desconectada",
                "Conecte a luva antes de iniciar o feedback."
            )
            return
        
        self.clear_screen()
        self.state.set_screen("feedback")
        try:
            self.active_screen = FeedbackScreen(master=self.root, app=self)
            logger.info("Tela de feedback carregada")
        except Exception as e:
            logger.error(f"Erro ao carregar tela de feedback: {e}", exc_info=True)
            self._show_error("Erro ao carregar feedback", str(e))
            self.show_main_screen()

    def show_history_screen(self):
        """Exibe a tela de histórico de sessões"""
        self.clear_screen()
        self.state.set_screen("history")
        try:
            self.active_screen = HistoryScreen(master=self.root, app=self)
            logger.info("Tela de histórico carregada")
        except Exception as e:
            logger.error(f"Erro ao carregar tela de histórico: {e}", exc_info=True)
            self._show_error("Erro ao carregar histórico", str(e))
            self.show_main_screen()

    # ============================================================
    # THREAD DA LUVA
    # ============================================================
    def start_connection(self):
        """
        Inicia thread de comunicação com a luva.
        Thread-safe e com limite de tentativas.
        """
        with self._thread_lock:
            # Verificar se já existe uma thread ativa
            if self.glove_thread and self.glove_thread.is_alive():
                logger.warning("Thread da luva já está ativa")
                return

            # Verificar limite de tentativas
            if self._connection_attempts >= self._max_connection_attempts:
                logger.error("Número máximo de tentativas de conexão atingido")
                self._show_error(
                    "Falha na Conexão",
                    "Não foi possível conectar à luva após várias tentativas.\n"
                    "Verifique:\n"
                    "• A luva está conectada?\n"
                    "• O GloveManager está fechado?\n"
                    "• A porta está correta?"
                )
                return

            try:
                logger.info(f"Iniciando conexão com a luva (tentativa {self._connection_attempts + 1})")
                
                self.glove_thread = GloveReaderThread(
                    output_queue=self.data_queue,
                    status_queue=self.status_queue,
                    c_exe_path=PATH_TO_C_EXE,
                    glove_port=GLOVE_CONNECTION_PORT,
                    sampling_rate=60,
                    debug=False,  # Mude para True se precisar de logs detalhados
                    auto_reconnect=True  # Reconexão automática
                )
                
                self.glove_thread.start()
                self._connection_attempts += 1
                logger.info("Thread da luva iniciada com sucesso")
                
            except Exception as e:
                logger.error(f"Erro ao iniciar thread da luva: {e}", exc_info=True)
                self.status_queue.put(f"error_start:{e}")
                self._show_error("Erro ao Conectar", f"Falha ao iniciar conexão: {e}")

    def stop_connection(self):
        """Para a thread da luva de forma segura"""
        with self._thread_lock:
            if self.glove_thread and self.glove_thread.is_alive():
                logger.info("Parando thread da luva...")
                try:
                    self.glove_thread.stop()
                    self.glove_thread.join(timeout=5)
                    logger.info("Thread da luva parada com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao parar thread: {e}", exc_info=True)
            
            self.glove_thread = None
            self.glove_connected = False

    def restart_connection(self):
        """Reinicia a conexão com a luva"""
        logger.info("Reiniciando conexão...")
        self.stop_connection()
        self._connection_attempts = 0  # Reset do contador
        self.start_connection()

    # ============================================================
    # ATUALIZAÇÕES PERIÓDICAS
    # ============================================================
    def _start_periodic_updates(self):
        """Inicia loops de atualização periódica"""
        if not self._updates_running:
            self._updates_running = True
            self.root.after(100, self.check_status)
            self.root.after(20, self.check_data)
            logger.debug("Atualizações periódicas iniciadas")

    def _stop_periodic_updates(self):
        """Para loops de atualização periódica"""
        self._updates_running = False
        logger.debug("Atualizações periódicas paradas")

    def check_status(self):
        """
        Lê mensagens de status da thread da luva:
            • connected - Luva conectada com sucesso
            • disconnected - Luva desconectada
            • error_xxx - Erro específico
            • stopped - Thread parada
        """
        if self._is_closing or not self._updates_running:
            return

        status_updated = False
        last_status = None
        try:
            while True:
                status = self.status_queue.get_nowait()
                # Diagnostics: print/log each dequeued status for debugging
                print(f"[DEBUG] check_status: dequeued status -> {status!r}")
                logger.debug("check_status: dequeued status -> %r", status)
                status_updated = True

                if status == "connected":
                    self.glove_connected = True
                    self._connection_attempts = 0  
                    logger.info("✓ Luva conectada")
                    print("[DEBUG] glove_connected set to True")

                elif status == "disconnected":
                    self.glove_connected = False
                    logger.warning("Luva desconectada")
                    print("[DEBUG] glove_connected set to False (disconnected)")

                elif isinstance(status, str) and status.startswith("error"):
                    self.glove_connected = False
                    self._handle_error(status)
                    print(f"[DEBUG] check_status: handled error status -> {status}")

                elif status == "stopped":
                    self.glove_connected = False
                    logger.info("Thread da luva parada")

                # remember last status dequeued for potential fallback
                last_status = status

        except queue.Empty:
            # Fila drenada -> atualizar UI se necessário
            if status_updated and hasattr(self.active_screen, "update_glove_status"):
                try:
                    # Preferir informar o estado booleano (mais comum nas telas).
                    # Se a tela esperar a string original, tentamos fallback.
                    print(f"[DEBUG] check_status: updating active_screen with glove_connected={self.glove_connected}")
                    self.active_screen.update_glove_status(self.glove_connected)
                except TypeError:
                    try:
                        logger.debug("update_glove_status rejected boolean, falling back to last_status=%r", last_status)
                        self.active_screen.update_glove_status(last_status)
                    except Exception as e:
                        logger.error(f"Erro ao atualizar status na tela (fallback): {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Erro ao atualizar status na tela: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Erro no check_status: {e}", exc_info=True)
        finally:
            if self._updates_running:
                self.root.after(200, self.check_status)

    def _handle_error(self, error_msg: str):
        """Trata erros vindos da thread da luva"""
        logger.error(f"Erro da thread: {error_msg}")
        
        # Extrair tipo de erro
        if ":" in error_msg:
            error_type = error_msg.split(":")[0].replace("error_", "")
            error_details = error_msg.split(":", 1)[1] if ":" in error_msg else ""
        else:
            error_type = error_msg.replace("error_", "")
            error_details = ""

        # Mensagens específicas por tipo de erro
        error_messages = {
            "executable_not_found": (
                "Executável Não Encontrado",
                f"O arquivo {PATH_TO_C_EXE} não foi encontrado.\n"
                "Verifique se o TestGlove64.exe está na pasta correta."
            ),
            "not_found": (
                "Arquivo Não Encontrado",
                "O executável da luva não foi encontrado."
            ),
            "permission": (
                "Erro de Permissão",
                "Sem permissão para acessar a porta.\n"
                "Tente executar como administrador."
            ),
            "timeout": (
                "Timeout",
                "A conexão com a luva expirou.\n"
                "Verifique a conexão USB."
            ),
        }

        title, message = error_messages.get(
            error_type,
            ("Erro de Conexão", f"Erro: {error_msg}")
        )

        if error_details:
            message += f"\n\nDetalhes: {error_details}"

        # Mostrar apenas se não estiver fechando
        if not self._is_closing:
            self.root.after(100, lambda: messagebox.showwarning(title, message))

    def check_data(self):
        """Lê pacotes de dados da fila e encaminha para a tela ativa."""
        if self._is_closing or not self._updates_running:
            return

        try:
            packets_processed = 0
            max_packets_per_cycle = 10

            while packets_processed < max_packets_per_cycle:
                raw = self.data_queue.get_nowait()
                packets_processed += 1

                # Tentar parsear com o processor
                gesture_id = None
                values = None
                try:
                    # parse_packet pode aceitar (raw, sensor_names) ou só raw
                    if hasattr(self.processor, "parse_packet"):
                        try:
                            parsed = self.processor.parse_packet(raw, SENSOR_NAMES)
                        except TypeError:
                            parsed = self.processor.parse_packet(raw)

                        if isinstance(parsed, tuple) and len(parsed) >= 2:
                            gesture_id, values = parsed[0], parsed[1]
                        elif isinstance(parsed, list):
                            values = parsed
                except Exception:
                    logger.exception("Falha ao parsear pacote: %r", raw)
                    continue

                if values is None:
                    continue

                # Filtrar / limpar valores se houver função
                try:
                    if hasattr(self.processor, "clean_values"):
                        values = self.processor.clean_values(values)
                except Exception:
                    logger.exception("Falha ao limpar valores")

                payload = (gesture_id, values)

                # Encaminhar para a tela ativa (a tela aceita tupla ou string)
                if hasattr(self.active_screen, "process_glove_data"):
                    try:
                        self.active_screen.process_glove_data(payload)
                    except Exception:
                        logger.exception("Erro em active_screen.process_glove_data")

        except queue.Empty:
            pass
        except Exception:
            logger.exception("Erro no check_data")
        finally:
            if self._updates_running:
                self.root.after(20, self.check_data)

    # ============================================================
    # UTILITÁRIOS
    # ============================================================
    def _show_error(self, title: str, message: str):
        """Exibe mensagem de erro thread-safe"""
        if not self._is_closing:
            self.root.after(0, lambda: messagebox.showerror(title, message))

    # ============================================================
    # EVENTO DE FECHAMENTO
    # ============================================================
    def on_close(self):
        """Fecha a aplicação de forma limpa e segura"""
        if self._is_closing:
            return
        
        if messagebox.askokcancel("Sair", "Deseja realmente encerrar o programa?"):
            logger.info("Encerrando aplicação...")
            self._is_closing = True
            
            # Parar atualizações periódicas
            self._stop_periodic_updates()
            
            # Parar thread da luva
            self.stop_connection()
            
            # Limpar filas
            try:
                while not self.data_queue.empty():
                    self.data_queue.get_nowait()
                while not self.status_queue.empty():
                    self.status_queue.get_nowait()
            except:
                pass
            
            # Destruir janela
            try:
                self.root.destroy()
                logger.info("Aplicação encerrada com sucesso")
            except Exception as e:
                logger.error(f"Erro ao destruir janela: {e}")