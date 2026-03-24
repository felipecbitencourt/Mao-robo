import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math

class GestosFeedback(tk.Frame):
    """
    Widget que mostra a imagem do gesto, um rótulo grande e uma lista compacta
    com os valores dos sensores + "amplitude máxima" (registro de menor valor,
    compatível com realtime_glove_feedback).
    Uso:
      gf = GestosFeedback(parent, size=320, images=imgs_dict, sensor_names=[...])
      gf.update_from_values(gesture_id, values, label_text="Gesto: X")
      gf.reset_max_amplitude()
    """

    def __init__(self, master, size=320, images_dir=None, images=None,
                 sensor_names=None, bg="white"):
        super().__init__(master, bg=bg)
        self.size = size
        self.bg = bg
        self.images = images or {}
        self.sensor_names = sensor_names or []
        self.default_image = None
        self.last_valid_gesture_id = None  # Armazena o último gesture_id válido

        # UI: imagem + labels
        top = tk.Frame(self, bg=bg)
        top.pack(fill="x", padx=6, pady=6)

        # imagem do gesto
        self.image_label = tk.Label(top, bg=bg)
        self.image_label.pack(side="left", padx=6)

        # área de texto grande com gesto e status
        txt_frame = tk.Frame(top, bg=bg)
        txt_frame.pack(side="left", fill="y", padx=8)

        self.gesture_big = tk.Label(txt_frame, text="Gesto: --", font=("Helvetica", 24, "bold"), bg=bg)
        self.gesture_big.pack(anchor="w", pady=(6,4))

        self.gesture_small = tk.Label(txt_frame, text="Estado: --", font=("Helvetica", 12), bg=bg, fg="#374151")
        self.gesture_small.pack(anchor="w")

        # controle de amplitude (reset)
        ctrl = tk.Frame(txt_frame, bg=bg)
        ctrl.pack(anchor="w", pady=(10,0))
        self.reset_btn = tk.Button(ctrl, text="Registrar nova sessão", command=self.reset_max_amplitude,
                                   bg="#06b6d4", fg="white")
        self.reset_btn.pack(side="left", padx=(0,6))
        self.last_ts_label = tk.Label(ctrl, text="", bg=bg, font=("Helvetica", 10))
        self.last_ts_label.pack(side="left")

        # carregar imagens se necessário (apenas se self.images vazio)
        if not self.images:
            if images_dir is None:
                images_dir = os.path.join(os.getcwd(), "assets", "gesture-images")
            try:
                if os.path.isdir(images_dir):
                    for fname in sorted(os.listdir(images_dir)):
                        base, _ = os.path.splitext(fname)
                        try:
                            key = int(base)
                        except Exception:
                            continue
                        path = os.path.join(images_dir, fname)
                        try:
                            img = Image.open(path).resize((self.size, self.size), Image.Resampling.LANCZOS)
                            self.images[key] = ImageTk.PhotoImage(img)
                        except Exception:
                            continue
            except Exception:
                self.images = {}

        self.default_image = self.images.get(-1)
        if self.default_image:
            self.image_label.config(image=self.default_image)
            self.image_label.image = self.default_image

        # ajustes do scroll region (removido)

    def _build_sensor_rows(self, count):
        # Remover o método completamente, pois não será mais usado
        pass

    def reset_max_amplitude(self):
        # reinicia o registro (seta valores altos para detectar novos mínimos)
        from datetime import datetime
        self.last_ts_label.config(text=f"Registrando: {datetime.now().strftime('%H:%M:%S')}")

    def update_from_values(self, gesture_id, values, label_text=None):
        """
        Atualiza imagem e labels a partir dos valores atuais.
        gesture_id: int or None
        values: iterable de floats
        label_text: texto opcional para o label principal
        """
        try:
            # garantir lista
            vals = list(values) if values is not None else []
        except Exception:
            vals = []

        # atualizar imagem
        try:
            gid = None
            if gesture_id is not None:
                try:
                    gid = int(gesture_id)
                    self.last_valid_gesture_id = gid  # Atualiza o último gesture_id válido
                except Exception:
                    gid = None
            else:
                gid = self.last_valid_gesture_id  # Usa o último gesture_id válido

            img = self.images.get(gid, self.default_image)
            if img:
                self.image_label.config(image=img)
                self.image_label.image = img
        except Exception:
            pass

        # atualizar labels do gesto
        try:
            if label_text is not None:
                self.gesture_big.config(text=label_text)
            else:
                self.gesture_big.config(text=f"Gesto: {gid if gid is not None else '--'}")
        except Exception:
            pass