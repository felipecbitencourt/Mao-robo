// Mão virtual 2D desenhada em canvas: espelha a abertura de cada dedo.
import { FINGERS, type Finger, type Openness } from './fingers';

interface FingerGeom { x: number; y: number; base: number; lengths: [number, number, number]; width: number }

const GEOM: Record<Finger, FingerGeom> = {
  polegar: { x: -70, y: 40, base: -130, lengths: [42, 34, 28], width: 30 },
  indicador: { x: -46, y: -62, base: -98, lengths: [50, 32, 26], width: 25 },
  medio: { x: -14, y: -70, base: -90, lengths: [56, 36, 28], width: 26 },
  anelar: { x: 18, y: -66, base: -84, lengths: [52, 33, 26], width: 25 },
  minimo: { x: 48, y: -52, base: -76, lengths: [40, 26, 22], width: 22 },
};

export function drawHand(canvas: HTMLCanvasElement, o: Openness, colors: { skin: string; edge: string; joint: string }) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth;
  const cssH = canvas.clientHeight;
  if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
  }
  const ctx = canvas.getContext('2d')!;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const scale = (Math.min(cssW, cssH) / 360) * dpr;
  ctx.setTransform(scale, 0, 0, scale, canvas.width / 2, canvas.height / 2 + 50 * scale);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Palma e punho
  ctx.fillStyle = colors.skin;
  ctx.strokeStyle = colors.edge;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.roundRect(-72, -80, 140, 150, [34, 34, 46, 46]);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.roundRect(-48, 66, 92, 60, 14);
  ctx.fill();
  ctx.stroke();

  // Dedos vistos de frente: ao fechar, cada falange "dobra" em direção à câmera e encurta
  // na projeção (cos do ângulo acumulado). O polegar gira no plano, em direção à palma.
  for (const f of FINGERS) if (f !== 'polegar') drawFinger(ctx, GEOM[f], o[f], colors, 'fold');
  drawFinger(ctx, GEOM.polegar, o.polegar, colors, 'swing');
}

function drawFinger(
  ctx: CanvasRenderingContext2D,
  g: FingerGeom,
  open: number,
  c: { skin: string; edge: string; joint: string },
  kind: 'fold' | 'swing',
) {
  const curl = (1 - open) * (kind === 'fold' ? 80 : 55); // graus por articulação
  let x = g.x;
  let y = g.y;
  let a = g.base;
  let phi = 0;
  const pts: [number, number][] = [[x, y]];
  g.lengths.forEach((len, i) => {
    if (kind === 'swing') {
      a += i === 0 ? curl * 0.8 : curl;
      const r = (a * Math.PI) / 180;
      x += Math.cos(r) * len;
      y += Math.sin(r) * len;
    } else {
      phi += curl;
      const r = (a * Math.PI) / 180;
      const proj = len * Math.cos((phi * Math.PI) / 180);
      x += Math.cos(r) * proj;
      y += Math.sin(r) * proj;
    }
    pts.push([x, y]);
  });
  // contorno + preenchimento
  for (const [w, color] of [[g.width + 5, c.edge], [g.width, c.skin]] as [number, string][]) {
    ctx.strokeStyle = color;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts.slice(1)) ctx.lineTo(p[0], p[1]);
    ctx.stroke();
  }
  ctx.fillStyle = c.joint;
  for (const p of pts.slice(1, -1)) {
    ctx.beginPath();
    ctx.arc(p[0], p[1], 3, 0, Math.PI * 2);
    ctx.fill();
  }
}
