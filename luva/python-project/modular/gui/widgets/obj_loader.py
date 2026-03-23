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


class OBJModel:
    """
    Minimal OBJ loader:
    - lê vértices (v ...) e faces (f ...).
    - triangula faces poligonais com fan triangulation.
    - scale aplica um fator de escala aos vértices.
    - draw() desenha em GL imediato (compatível com o pipeline usado pelo canvas).
    - self.valid indica sucesso no carregamento.
    """
    def __init__(self, path: str, scale: float = 1.0):
        self.path = path
        self.scale = float(scale)
        self.vertices = []  # list of (x,y,z)
        self.texcoords = []  # list of (u,v)
        self.normals = []    # list of (nx,ny,nz)
        # faces: list of lists of tuples (vi, ti, ni) where items may be None
        self.faces = []
        # optional material per face (parallel to self.faces)
        self.face_materials = []
        self.valid = True

        # parse OBJ with support for object/group sections so we can treat
        # sub-meshes independently (useful to animate fingers as rigid parts)
        current_group = "default"
        self.groups = {}  # name -> list of face indices (indices into self.faces)
        self.materials = {}  # name -> dict(parsed from .mtl)
        self._loaded_textures = {}  # cache loaded pyglet textures
        current_material = None
        try:
            basedir = os.path.dirname(path)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line:
                        continue
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("mtllib "):
                        # load referenced MTL (best-effort)
                        parts = line.split(maxsplit=1)
                        if len(parts) > 1:
                            mtl_name = parts[1].strip()
                            mtl_path = os.path.join(basedir, mtl_name)
                            if os.path.exists(mtl_path):
                                try:
                                    self._load_mtl(mtl_path)
                                except Exception:
                                    pass
                    elif line.startswith("o ") or line.startswith("g "):
                        parts = line.split(maxsplit=1)
                        if len(parts) > 1 and parts[1].strip():
                            current_group = parts[1].strip()
                        else:
                            current_group = "default"
                        if current_group not in self.groups:
                            self.groups[current_group] = []
                    elif line.startswith("usemtl "):
                        parts = line.split(maxsplit=1)
                        if len(parts) > 1:
                            current_material = parts[1].strip()
                    elif line.startswith("v "):
                        parts = line.split()
                        if len(parts) >= 4:
                            x, y, z = map(float, parts[1:4])
                            self.vertices.append((x * self.scale, y * self.scale, z * self.scale))
                    elif line.startswith("vt "):
                        parts = line.split()
                        if len(parts) >= 3:
                            u, v = map(float, parts[1:3])
                            self.texcoords.append((u, v))
                    elif line.startswith("vn "):
                        parts = line.split()
                        if len(parts) >= 4:
                            nx, ny, nz = map(float, parts[1:4])
                            self.normals.append((nx, ny, nz))
                    elif line.startswith("f "):
                        parts = line.split()[1:]
                        face = []
                        for p in parts:
                            # face items can be v, v/vt, v//vn, v/vt/vn
                            vi = ti = ni = None
                            items = p.split('/')
                            try:
                                if len(items) >= 1 and items[0]:
                                    vi = int(items[0]) - 1
                            except Exception:
                                vi = None
                            try:
                                if len(items) >= 2 and items[1]:
                                    ti = int(items[1]) - 1
                            except Exception:
                                ti = None
                            try:
                                if len(items) >= 3 and items[2]:
                                    ni = int(items[2]) - 1
                            except Exception:
                                ni = None
                            if vi is None:
                                # malformed, skip this vertex
                                continue
                            face.append((vi, ti, ni))
                        if len(face) >= 3:
                            face_idx = len(self.faces)
                            self.faces.append(face)
                            self.face_materials.append(current_material)
                            # attach face to current group
                            if current_group not in self.groups:
                                self.groups[current_group] = []
                            self.groups[current_group].append(face_idx)
        except Exception as e:
            # falha ao abrir/parsear -> marca inválido
            print(f"[OBJModel] erro ao carregar {path}: {e}")
            self.valid = False

        if not self.vertices or not self.faces:
            # arquivo possivelmente vazio ou não suportado
            self.valid = False

        # compute bounding box, center and max extent for convenient framing
        if self.vertices:
            xs = [v[0] for v in self.vertices]
            ys = [v[1] for v in self.vertices]
            zs = [v[2] for v in self.vertices]
            self.bbox_min = (min(xs), min(ys), min(zs))
            self.bbox_max = (max(xs), max(ys), max(zs))
            cx = (self.bbox_min[0] + self.bbox_max[0]) / 2.0
            cy = (self.bbox_min[1] + self.bbox_max[1]) / 2.0
            cz = (self.bbox_min[2] + self.bbox_max[2]) / 2.0
            self.center = (cx, cy, cz)
            size_x = self.bbox_max[0] - self.bbox_min[0]
            size_y = self.bbox_max[1] - self.bbox_min[1]
            size_z = self.bbox_max[2] - self.bbox_min[2]
            self.max_extent = max(size_x, size_y, size_z, 1e-9)
        else:
            # defaults to avoid crash
            self.bbox_min = (0.0, 0.0, 0.0)
            self.bbox_max = (0.0, 0.0, 0.0)
            self.center = (0.0, 0.0, 0.0)
            self.max_extent = 1.0

        # ---- START ADD: post-load diagnostics & validation ----
        # counts
        self.vertex_count = len(self.vertices)
        self.face_count = len(self.faces)

        # check for faces referencing invalid indices
        max_ref = None
        if self.faces:
            try:
                # faces are lists of tuples (vi, ti, ni) where vi may be None
                max_ref = max(
                    vi for face in self.faces for (vi, ti, ni) in face if vi is not None
                )
            except Exception:
                max_ref = None

        if max_ref is not None and isinstance(max_ref, int) and max_ref >= self.vertex_count:
            # report invalid referencing (note: face indices are 0-based here)
            print(f"[OBJModel] WARNING: face references index {max_ref+1} but only {self.vertex_count} vertices were loaded.")
            # mark as invalid to avoid rendering garbage
            self.valid = False
        else:
            # print helpful summary for debugging
            print(f"[OBJModel] Loaded: {os.path.basename(self.path)} | verts={self.vertex_count} faces={self.face_count} "
                  f"bbox_min={self.bbox_min} bbox_max={self.bbox_max} center={self.center} max_extent={self.max_extent:.6f}")
        # ---- END ADD ----

        # compute per-group vertex sets and centers for use as local pivots
        self.group_vertices = {}
        self.group_centers = {}
        try:
            for name, face_idxs in self.groups.items():
                vset = set()
                for fi in face_idxs:
                    # each face is a list of tuples (vi,ti,ni)
                    for vertex in self.faces[fi]:
                        try:
                            vi, ti, ni = vertex
                        except Exception:
                            continue
                        if vi is not None:
                            vset.add(vi)
                self.group_vertices[name] = vset
                if vset:
                    xs = [self.vertices[i][0] for i in vset]
                    ys = [self.vertices[i][1] for i in vset]
                    zs = [self.vertices[i][2] for i in vset]
                    self.group_centers[name] = (sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs))
                else:
                    self.group_centers[name] = (0.0, 0.0, 0.0)
        except Exception:
            # non-fatal
            pass

        # If the model has very few groups (e.g. exported as two halves),
        # optionally generate automatic vertical slices so the viewer can
        # approximate per-finger articulation. This is a heuristic fallback
        # when the OBJ doesn't provide per-finger groups. You can control
        # the number of auto-slices via env var BRAIN_GLOVE_AUTO_SPLIT.
        try:
            auto_slices = os.environ.get("BRAIN_GLOVE_AUTO_SPLIT", "")
            if auto_slices:
                N = int(auto_slices)
            else:
                # create auto-slices when there are less than 5 groups
                N = 6 if len(self.groups) < 5 else 0
        except Exception:
            N = 0

        if N and len(self.vertices) > 10:
            # bucket vertices along X axis into N slices
            xs = [v[0] for v in self.vertices]
            minx, maxx = min(xs), max(xs)
            span = maxx - minx if maxx > minx else 1e-6
            width = span / float(N)
            vertex_bucket = {}
            for i, v in enumerate(self.vertices):
                bx = int((v[0] - minx) / width)
                if bx < 0:
                    bx = 0
                if bx >= N:
                    bx = N - 1
                vertex_bucket[i] = bx

            auto_groups = {f"auto_{i}": [] for i in range(N)}
            # assign faces to bucket where majority of vertices lie
            for fi, face in enumerate(self.faces):
                counts = {}
                for (vi, ti, ni) in face:
                    b = vertex_bucket.get(vi, 0)
                    counts[b] = counts.get(b, 0) + 1
                # pick bucket with max count
                best = max(counts.items(), key=lambda x: x[1])[0]
                auto_groups[f"auto_{best}"].append(fi)

            # remove empty buckets
            auto_groups = {k: v for k, v in auto_groups.items() if v}
            # replace groups with non-empty auto_groups (useful for viewers expecting finger parts)
            if auto_groups:
                self.groups = auto_groups
            # recompute group_vertices and centers for the auto groups
            self.group_vertices = {}
            self.group_centers = {}
            for name, face_idxs in self.groups.items():
                vset = set()
                for fi in face_idxs:
                    for vertex in self.faces[fi]:
                        try:
                            vi, ti, ni = vertex
                        except Exception:
                            continue
                        if vi is not None:
                            vset.add(vi)
                self.group_vertices[name] = vset
                if vset:
                    xs = [self.vertices[i][0] for i in vset]
                    ys = [self.vertices[i][1] for i in vset]
                    zs = [self.vertices[i][2] for i in vset]
                    self.group_centers[name] = (sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs))
                else:
                    self.group_centers[name] = (0.0, 0.0, 0.0)

    def draw(self):
        if not self.valid:
            return
        try:
            # desenhar faces (usando possíveis UVs/texture e normals)
            for fi, face in enumerate(self.faces):
                # determine primitive triangles (fan triangulation)
                if len(face) == 3:
                    tris = [(face[0], face[1], face[2])]
                else:
                    tris = []
                    for i in range(1, len(face) - 1):
                        tris.append((face[0], face[i], face[i+1]))

                # material/texture bind if present
                mname = None
                if fi < len(self.face_materials):
                    mname = self.face_materials[fi]
                tex = None
                color = (0.85, 0.85, 0.85)
                if mname and mname in self.materials:
                    mat = self.materials[mname]
                    if mat.get("map_Kd"):
                        texpath = mat.get("map_Kd")
                        try:
                            tex = self._get_texture(texpath)
                        except Exception:
                            tex = None
                    if mat.get("Kd"):
                        color = mat.get("Kd")

                if tex:
                    gl.glEnable(gl.GL_TEXTURE_2D)
                    gl.glBindTexture(gl.GL_TEXTURE_2D, tex.id)
                else:
                    gl.glDisable(gl.GL_TEXTURE_2D)
                    gl.glColor3f(*color)

                for a,b,c in tris:
                    gl.glBegin(gl.GL_TRIANGLES)
                    for vertex in (a,b,c):
                        vi, ti, ni = vertex
                        if ti is not None and 0 <= ti < len(self.texcoords) and tex:
                            u,v = self.texcoords[ti]
                            gl.glTexCoord2f(float(u), float(v))
                        if ni is not None and 0 <= ni < len(self.normals):
                            nx, ny, nz = self.normals[ni]
                            gl.glNormal3f(nx, ny, nz)
                        vx, vy, vz = self.vertices[vi]
                        gl.glVertex3f(vx, vy, vz)
                    gl.glEnd()
                # unbind texture after face (fine-grained; we could batch by material in future)
                if tex:
                    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            # ensure texturing disabled after draw
            gl.glDisable(gl.GL_TEXTURE_2D)
        except Exception as e:
            # evita quebrar o loop de render
            print("[OBJModel] erro ao desenhar:", e)
            self.valid = False

    # ---- START ADD: debug draw helpers ----
    def draw_wireframe(self):
        """Desenha as faces como linhas (útil para ver topology)."""
        if not self.valid:
            return
        try:
            gl.glColor3f(0.2, 0.9, 0.2)
            for face in self.faces:
                gl.glBegin(gl.GL_LINE_LOOP)
                for vi,ti,ni in face:
                    v = self.vertices[vi]
                    gl.glVertex3f(v[0], v[1], v[2])
                gl.glEnd()
        except Exception as e:
            print("[OBJModel] erro wireframe:", e)

    def draw_points(self, size: float = 4.0):
        """Desenha os vértices como pontos (útil para ver se estão todos concentrados)."""
        if not self.valid:
            return
        try:
            gl.glPointSize(float(size))
            gl.glColor3f(1.0, 1.0, 0.0)
            gl.glBegin(gl.GL_POINTS)
            for v in self.vertices:
                gl.glVertex3f(v[0], v[1], v[2])
            gl.glEnd()
        except Exception as e:
            print("[OBJModel] erro pontos:", e)

    def draw_bbox(self):
        """Desenha a bounding box (linhas) calculada no carregamento."""
        try:
            minx, miny, minz = self.bbox_min
            maxx, maxy, maxz = self.bbox_max
            corners = [
                (minx, miny, minz), (maxx, miny, minz),
                (maxx, maxy, minz), (minx, maxy, minz),
                (minx, miny, maxz), (maxx, miny, maxz),
                (maxx, maxy, maxz), (minx, maxy, maxz),
            ]
            edges = [
                (0,1),(1,2),(2,3),(3,0),
                (4,5),(5,6),(6,7),(7,4),
                (0,4),(1,5),(2,6),(3,7),
            ]
            gl.glColor3f(0.9, 0.2, 0.2)
            for a,b in edges:
                gl.glBegin(gl.GL_LINES)
                gl.glVertex3f(*corners[a])
                gl.glVertex3f(*corners[b])
                gl.glEnd()
        except Exception as e:
            print("[OBJModel] erro bbox:", e)
    # ---- END ADD ----

    def draw_group(self, name: str):
        """Desenha um grupo/sub-mesh identificado por `name`."""
        if not self.valid:
            return
        if name not in self.groups:
            return
        try:
            # draw faces for the group, honouring materials & UVs if available
            for fi in self.groups[name]:
                if fi < 0 or fi >= len(self.faces):
                    continue
                face = self.faces[fi]
                # triangulate
                if len(face) == 3:
                    tris = [(face[0], face[1], face[2])]
                else:
                    tris = []
                    for i in range(1, len(face) - 1):
                        tris.append((face[0], face[i], face[i+1]))

                # material for this face
                mname = None
                if fi < len(self.face_materials):
                    mname = self.face_materials[fi]
                tex = None
                color = (0.85, 0.85, 0.85)
                if mname and mname in self.materials:
                    mat = self.materials[mname]
                    if mat.get("map_Kd"):
                        try:
                            tex = self._get_texture(mat.get("map_Kd"))
                        except Exception:
                            tex = None
                    if mat.get("Kd"):
                        color = mat.get("Kd")

                if tex:
                    gl.glEnable(gl.GL_TEXTURE_2D)
                    gl.glBindTexture(gl.GL_TEXTURE_2D, tex.id)
                else:
                    gl.glDisable(gl.GL_TEXTURE_2D)
                    gl.glColor3f(*color)

                for a,b,c in tris:
                    gl.glBegin(gl.GL_TRIANGLES)
                    for vertex in (a,b,c):
                        vi, ti, ni = vertex
                        if ti is not None and 0 <= ti < len(self.texcoords) and tex:
                            u,v = self.texcoords[ti]
                            gl.glTexCoord2f(float(u), float(v))
                        if ni is not None and 0 <= ni < len(self.normals):
                            nx, ny, nz = self.normals[ni]
                            gl.glNormal3f(nx, ny, nz)
                        vx, vy, vz = self.vertices[vi]
                        gl.glVertex3f(vx, vy, vz)
                    gl.glEnd()

                if tex:
                    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        except Exception as e:
            print(f"[OBJModel] erro ao desenhar grupo {name}:", e)

    # ---- START ADD: MTL parsing and texture helpers ----
    def _load_mtl(self, mtl_path: str):
        """Parse a minimal subset of MTL: newmtl, Kd and map_Kd."""
        cur = None
        basedir = os.path.dirname(mtl_path)
        try:
            with open(mtl_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line:
                        continue
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('newmtl '):
                        cur = line.split(maxsplit=1)[1].strip()
                        self.materials[cur] = {}
                    elif cur is None:
                        continue
                    elif line.startswith('Kd '):
                        parts = line.split()
                        try:
                            r,g,b = map(float, parts[1:4])
                            self.materials[cur]['Kd'] = (r,g,b)
                        except Exception:
                            pass
                    elif line.startswith('map_Kd '):
                        parts = line.split(maxsplit=1)
                        if len(parts) > 1:
                            imgname = parts[1].strip()
                            imgpath = os.path.join(basedir, imgname)
                            # store absolute path when possible
                            if os.path.exists(imgpath):
                                self.materials[cur]['map_Kd'] = imgpath
                            else:
                                self.materials[cur]['map_Kd'] = imgname
        except Exception as e:
            print(f"[OBJModel] warning: failed to parse MTL {mtl_path}: {e}")

    def _get_texture(self, imgpath: str):
        """Load texture via pyglet (cached). imgpath may be absolute or relative to OBJ dir."""
        # if already cached
        if imgpath in self._loaded_textures:
            return self._loaded_textures[imgpath]
        # try absolute first
        candidate = imgpath
        if not os.path.exists(candidate):
            # try relative to OBJ path
            candidate = os.path.join(os.path.dirname(self.path), imgpath)
        if not os.path.exists(candidate):
            # try also the models/ folder as fallback
            candidate = os.path.join(os.path.dirname(os.path.dirname(self.path)), 'models', imgpath)
        if not os.path.exists(candidate):
            raise FileNotFoundError(imgpath)
        try:
            img = pyglet.image.load(candidate)
            tex = img.get_texture()
            # ensure texture parameters (basic nearest/mipmapping not configured)
            gl.glBindTexture(gl.GL_TEXTURE_2D, tex.id)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            self._loaded_textures[imgpath] = tex
            return tex
        except Exception as e:
            raise
    # ---- END ADD ----

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
            from gui.widgets.vector_viewer.obj_loader import OBJModel
            if os.path.exists(self.obj_path):
                print(f"[OpenGLCanvas] Carregando OBJ: {self.obj_path}")
                self.obj_model = OBJModel(self.obj_path, scale=1.0)
                if getattr(self.obj_model, "valid", True) is False:
                    print("[OpenGLCanvas] OBJ carregado porém inválido. Render será desativado para esse modelo.")
                    self.obj_model = None
                else:
                    # manter centro (usado para centralizar via translate)
                    self._model_center = getattr(self.obj_model, "center", (0.0, 0.0, 0.0))
            else:
                print(f"[OpenGLCanvas] Arquivo OBJ não encontrado: {self.obj_path}")
                self.obj_model = None
                self._model_center = (0.0, 0.0, 0.0)
        except Exception as e:
            print("[OpenGLCanvas] Erro ao importar/abrir OBJModel:", e)
            self.obj_model = None
            self._model_center = (0.0, 0.0, 0.0)

        # ---- START ADD: GL debug flag from env and model summary ----
        # enable optional GL debug drawing via environment variable:
        self._gl_debug = bool(os.environ.get("BRAIN_GLOVE_GL_DEBUG", "").strip())
        if self._gl_debug:
            print("[OpenGLCanvas] GL DEBUG habilitado (wireframe/points/bbox)")

        # fit fraction (how much of the view height the model should occupy)
        try:
            fit_env = os.environ.get("BRAIN_GLOVE_GL_FIT", "").strip()
            if fit_env:
                fit = float(fit_env)
            else:
                fit = 0.9
        except Exception:
            fit = 0.9
        # clamp sensible range
        fit = max(0.1, min(0.99, fit))
        self._gl_fit_fraction = fit
        if self.obj_model is not None:
            print(f"[OpenGLCanvas] Modelo OK: verts={getattr(self.obj_model,'vertex_count',0)} faces={getattr(self.obj_model,'face_count',0)} "
                  f"center={getattr(self.obj_model,'center',None)} max_extent={getattr(self.obj_model,'max_extent',None)} fit_fraction={self._gl_fit_fraction}")
        # ---- END ADD ----

        # estado para animação/debug
        self._rotation = 0.0
        # ...remove hardcoded original _scale assignment earlier if present...
        # assegura que _scale/_model_center existam
        if not hasattr(self, "_scale"):
            self._scale = 0.12
        if not hasattr(self, "_model_center"):
            self._model_center = (0.0, 0.0, 0.0)

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

            # ---- START CHANGE: compute ortho size from fit fraction ----
            if getattr(self, "obj_model", None) is not None and getattr(self.obj_model, "max_extent", None):
                E = float(self.obj_model.max_extent)
                fit = getattr(self, "_gl_fit_fraction", 0.9)
                # size is the half-height of the ortho. To make the model (extent E)
                # occupy 'fit' fraction of the full height (2*size), we need:
                # E = fit * (2*size) -> size = E / (2*fit)
                size = max(E / (2.0 * fit), 1e-6)
                # debug print once per frame might be noisy; print only if debug enabled
                if getattr(self, "_gl_debug", False):
                    print(f"[OpenGLCanvas] ortho size computed -> {size:.6f} (E={E:.6f}, fit={fit})")
            else:
                # fallback
                size = 1.0
            gl.glOrtho(-size * aspect, size * aspect, -size, size, -100.0, 100.0)
            # ---- END CHANGE ----

            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glLoadIdentity()

            # aplicar transform mínima para visualizar o objeto
            gl.glPushMatrix()
            try:
                # ---- START CHANGE: center model via translation, avoid arbitrary scale ----
                try:
                    cx, cy, cz = getattr(self, "_model_center", getattr(self.obj_model, "center", (0.0, 0.0, 0.0)))
                    gl.glTranslatef(-cx, -cy, -cz)
                except Exception:
                    pass
                # não aplicar glScalef aqui — a ortho 'size' foi ajustada para encaixar o modelo
                # rodar para debug (visível)
                gl.glRotatef(25, 1.0, 0.0, 0.0)
                gl.glRotatef(self._rotation, 0.0, 1.0, 0.0)
                self._rotation = (self._rotation + 0.4) % 360.0
                # ---- END CHANGE ----

                if self.obj_model is not None:
                    # desenho principal
                    self.obj_model.draw()

                    # calls de debug (condicionais)
                    if getattr(self, "_gl_debug", False):
                        # desenha wireframe por cima
                        gl.glDisable(gl.GL_LIGHTING) if hasattr(gl, "glDisable") else None
                        self.obj_model.draw_wireframe()
                        # desenha bounding box
                        self.obj_model.draw_bbox()
                        # desenha vértices (pontos) — ajuda a ver concentração
                        self.obj_model.draw_points(size=5.0)
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
