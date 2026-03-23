# openGL_canvas.py
# OpenGLCanvas — Frame Tkinter com janela pyglet embutida
# Suporte a carregamento de modelo OBJ, projeção mínima e depth test.
# Coloque em: modular/gui/widgets/vector_viewer/openGL_canvas.py

import os
import threading
import tkinter as tk
from pathlib import Path

try:
    import pyglet
    from pyglet import gl
except Exception as e:
    raise ImportError("pyglet é necessário: pip install pyglet") from e


class OpenGLCanvas(tk.Frame):
    def __init__(self, master, obj_path: str | None = None,
                 width: int = 640, height: int = 480,
                 vsync: bool = True, fps: int = 60, **kwargs):
        """
        obj_path: caminho absoluto ou relativo para o modelo .obj.
                  Se None, será resolvido automaticamente para
                  modular/assets/models/hand.obj (a partir deste arquivo).
        """
        super().__init__(master, width=width, height=height, **kwargs)

        self.master = master
        self.width = width
        self.height = height
        self.vsync = vsync
        self.fps = fps

        # resolve default obj_path (a partir da raiz modular/)
        if obj_path is None:
            # __file__ -> modular/gui/widgets/vector_viewer/openGL_canvas.py
            base = Path(__file__).resolve()
            # parents[3] -> modular/
            project_root = base.parents[3]
            default = project_root / "assets" / "models" / "hand.obj"
            obj_path = str(default)

        # normalize to absolute
        self.obj_path = os.path.abspath(obj_path)
        print(f"[OpenGLCanvas] OBJ path -> {self.obj_path}")

        self.obj_model = None

        # bind resize
        self.bind("<Configure>", self._on_configure)

        # pyglet window references
        self._pyglet_window = None
        self._pyglet_thread = None
        self._should_stop = threading.Event()

        # temporary label until pyglet window overlays the frame
        self._label = tk.Label(self, text="OpenGL Canvas (pyglet)", bg="#111", fg="#fff")
        self._label.place(relx=0.5, rely=0.5, anchor="center")

        # start pyglet loop in background
        self._start_pyglet_thread()

    # -------------------------
    def _on_configure(self, event):
        self.width = event.width
        self.height = event.height
        if self._pyglet_window:
            self._reposition_pyglet_window()

    # -------------------------
    def _start_pyglet_thread(self):
        if self._pyglet_thread and self._pyglet_thread.is_alive():
            return
        self._pyglet_thread = threading.Thread(target=self._pyglet_main, daemon=True)
        self._pyglet_thread.start()

    # -------------------------
    def _pyglet_main(self):
        # criar janela pyglet
        try:
            window = pyglet.window.Window(width=self.width, height=self.height,
                                          vsync=self.vsync, caption="OpenGL Canvas")
        except Exception:
            window = pyglet.window.Window(width=self.width, height=self.height)

        self._pyglet_window = window

        # -- OpenGL setup once
        try:
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthFunc(gl.GL_LESS)
        except Exception:
            # se algum backend não suportar, seguimos sem depth
            pass

        # carregar modelo OBJ (se existir)
        try:
            from gui.widgets.obj_loader import OBJModel
            if os.path.exists(self.obj_path):
                print(f"[OpenGLCanvas] Carregando OBJ: {self.obj_path}")
                self.obj_model = OBJModel(self.obj_path, scale=1.0)
                if getattr(self.obj_model, "valid", True) is False:
                    print("[OpenGLCanvas] OBJ carregado porém inválido.")
                    self.obj_model = None
            else:
                print(f"[OpenGLCanvas] Arquivo OBJ não encontrado: {self.obj_path}")
                self.obj_model = None
        except Exception as e:
            print("[OpenGLCanvas] Erro ao importar/abrir OBJModel:", e)
            self.obj_model = None

        # estado para animação/debug
        self._rotation = 0.0
        # optional GL debug & fit fraction controlled via environment
        self._gl_debug = bool(os.environ.get("BRAIN_GLOVE_GL_DEBUG", "").strip())
        try:
            fit_env = os.environ.get("BRAIN_GLOVE_GL_FIT", "").strip()
            if fit_env:
                fit = float(fit_env)
            else:
                fit = 0.9
        except Exception:
            fit = 0.9
        fit = max(0.1, min(0.99, fit))
        self._gl_fit_fraction = fit

        # keep a model center (used to translate model to origin)
        if self.obj_model is not None:
            self._model_center = getattr(self.obj_model, "center", (0.0, 0.0, 0.0))
            print(f"[OpenGLCanvas] Modelo OK: verts={getattr(self.obj_model,'vertex_count',0)} faces={getattr(self.obj_model,'face_count',0)} "
                  f"center={getattr(self.obj_model,'center',None)} max_extent={getattr(self.obj_model,'max_extent',None)} fit_fraction={self._gl_fit_fraction}")
        else:
            self._model_center = (0.0, 0.0, 0.0)

        # rotations per group (name -> angle degrees)
        self._group_rotations = {}

        # --- evento de desenho
        @window.event
        def on_draw():
            # limpar buffers
            gl.glClearColor(0.05, 0.05, 0.05, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            # configurar viewport/projection (simples ortho -> fácil e previsível)
            gl.glViewport(0, 0, window.width, window.height)

            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glLoadIdentity()
            # usar ortho para evitar dependências do GLU
            aspect = window.width / max(1.0, window.height)

            # compute ortho size from model extent so model fits the view
            if getattr(self, "obj_model", None) is not None and getattr(self.obj_model, "max_extent", None):
                E = float(self.obj_model.max_extent)
                fit = getattr(self, "_gl_fit_fraction", 0.9)
                # size is the half-height of the ortho. To make the model (extent E)
                # occupy 'fit' fraction of the full height (2*size): size = E/(2*fit)
                size = max(E / (2.0 * fit), 1e-6)
                if getattr(self, "_gl_debug", False):
                    print(f"[OpenGLCanvas] ortho size computed -> {size:.6f} (E={E:.6f}, fit={fit})")
            else:
                size = 1.0

            gl.glOrtho(-size * aspect, size * aspect, -size, size, -100.0, 100.0)

            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glLoadIdentity()

            # aplicar transform mínima para visualizar o objeto
            gl.glPushMatrix()
            try:
                # centralizar o modelo via translação (a ortho já ajusta o zoom)
                try:
                    cx, cy, cz = getattr(self, "_model_center", getattr(self.obj_model, "center", (0.0, 0.0, 0.0)))
                    gl.glTranslatef(-cx, -cy, -cz)
                except Exception:
                    pass

                # rodar para debug (visível)
                gl.glRotatef(25, 1.0, 0.0, 0.0)
                gl.glRotatef(self._rotation, 0.0, 1.0, 0.0)
                self._rotation = (self._rotation + 0.4) % 360.0

                if self.obj_model is not None:
                    # draw each group individually so we can apply per-group transforms
                    try:
                        # optional GL debug overlays (wireframe + bbox)
                        if getattr(self, "_gl_debug", False) and getattr(self.obj_model, "valid", False):
                            try:
                                self.obj_model.draw_wireframe()
                                self.obj_model.draw_bbox()
                            except Exception as e:
                                print("[OpenGLCanvas] debug overlay failed:", e)
                        groups = getattr(self.obj_model, 'groups', None)
                        if groups:
                            # after we already translated the model by -model_center,
                            # group centers must be converted to local coordinates
                            mcx, mcy, mcz = getattr(self, '_model_center', (0.0, 0.0, 0.0))
                            for gname in groups.keys():
                                # apply transform for this group around its local centroid
                                gx, gy, gz = self.obj_model.group_centers.get(gname, (0.0, 0.0, 0.0))
                                lx, ly, lz = gx - mcx, gy - mcy, gz - mcz
                                angle = self._group_rotations.get(gname, 0.0)
                                gl.glPushMatrix()
                                try:
                                    # translate to group's local pivot, rotate, translate back
                                    gl.glTranslatef(lx, ly, lz)
                                    gl.glRotatef(angle, 1.0, 0.0, 0.0)
                                    gl.glTranslatef(-lx, -ly, -lz)
                                    self.obj_model.draw_group(gname)
                                finally:
                                    gl.glPopMatrix()
                        else:
                            # no groups available -> draw whole model
                            self.obj_model.draw()
                    except Exception:
                        # fallback
                        self.obj_model.draw()
                else:
                    # fallback — triângulo colorido (garante que o pipeline está OK)
                    gl.glBegin(gl.GL_TRIANGLES)
                    gl.glColor3f(1.0, 0.0, 0.0)
                    gl.glVertex3f(-0.5, -0.5, 0.0)
                    gl.glColor3f(0.0, 1.0, 0.0)
                    gl.glVertex3f(0.5, -0.5, 0.0)
                    gl.glColor3f(0.0, 0.0, 1.0)
                    gl.glVertex3f(0.0, 0.5, 0.0)
                    gl.glEnd()
            finally:
                gl.glPopMatrix()

        # update loop: processa eventos e redesenha
        def update(dt):
            # stealth dispatch events (garante responsividade)
            window.dispatch_events()
            window.dispatch_event("on_draw")

        pyglet.clock.schedule_interval(update, 1.0 / max(1, self.fps))

        # posicionar a janela pyglet sobre o frame do Tkinter
        self._reposition_pyglet_window()

        # roda o app pyglet (bloqueia a thread)
        pyglet.app.run()

    # ----------------------------------------------------------------------
    # mover janela pyglet para coincidir com o Frame Tkinter
    # ----------------------------------------------------------------------
     # -------------------------
    def _reposition_pyglet_window(self):
        if self._pyglet_window is None:
            return
        try:
            rx = self.winfo_rootx()
            ry = self.winfo_rooty()
            # mover e redimensionar a janela pyglet para cobrir o Frame Tkinter
            self._pyglet_window.set_location(rx, ry)
            self._pyglet_window.set_size(self.width, self.height)
        except Exception:
            # em alguns desktops/backends isso pode falhar — ignorar
            pass

    # -------------------------
    def update_vector(self, vec):
        """Recebe um vetor de valores (por exemplo controles por dedo) e atualiza
        rotações por grupo. `vec` pode ser um escalar, ou um iterável com valores
        por dedo. Valores devem estar aproximadamente em [0,1]; são mapeados para
        ângulos em graus.
        """
        try:
            # gather group names that look like fingers
            groups = list(getattr(self.obj_model, 'groups', {}).keys()) if self.obj_model else []
            # mapping order we expect in vec -> prefer matching by name
            name_order = ['index', 'middle', 'ring', 'pinky', 'thumb']

            # normalize vec to list
            if vec is None:
                return
            if isinstance(vec, (int, float)):
                vals = [float(vec)]
            else:
                try:
                    vals = [float(x) for x in vec]
                except Exception:
                    vals = [float(vec)]

            # max curl angle
            max_angle = 65.0

            # try to match groups by keywords and assign values
            assigned = {}
            vi = 0
            for key in name_order:
                # find first group containing key
                for g in groups:
                    if key in g.lower() and g not in assigned:
                        v = vals[vi] if vi < len(vals) else vals[-1]
                        angle = max(-180.0, min(180.0, float(v) * max_angle))
                        assigned[g] = angle
                        vi += 1
                        break

            # if nothing matched, try positional assignment (left->right) so
            # sensors map to spatially ordered groups. Fallback: apply first
            # value to all groups if positional assignment not possible.
            if not assigned and groups:
                try:
                    # order groups by X coordinate of their center (descending)
                    groups_sorted = sorted(groups, key=lambda g: self.obj_model.group_centers.get(g, (0.0,0.0,0.0))[0], reverse=True)
                    for i, g in enumerate(groups_sorted):
                        v = vals[i] if i < len(vals) else vals[-1]
                        angle = max(-180.0, min(180.0, float(v) * max_angle))
                        assigned[g] = angle
                except Exception:
                    v = vals[0]
                    angle = max(-180.0, min(180.0, float(v) * max_angle))
                    for g in groups:
                        assigned[g] = angle

            # commit to _group_rotations
            for gname, a in assigned.items():
                self._group_rotations[gname] = a
        except Exception:
            pass

    # -------------------------
    def stop(self):
        try:
            pyglet.app.exit()
        except Exception:
            pass

    def destroy(self):
        self.stop()
        super().destroy()


# teste rápido
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x700")

    # se quiser forçar outro caminho, passe obj_path="
    canvas = OpenGLCanvas(root, obj_path=None, bg="#222")
    canvas.pack(expand=True, fill="both", padx=8, pady=8)

    def on_close():
        canvas.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
