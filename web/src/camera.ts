// Rastreamento da mão pela webcam com MediaPipe Tasks Vision (porte de src/processing/hand_processor.py).
import { FilesetResolver, HandLandmarker, type NormalizedLandmark } from '@mediapipe/tasks-vision';
import { clamp01, FINGERS, KalmanFilter, type Finger, type Openness } from './fingers';

type Pt = [number, number];

const INDICES: Record<Exclude<Finger, 'polegar'>, { mcp: [number, number, number]; pip: [number, number, number] }> = {
  indicador: { mcp: [0, 5, 6], pip: [5, 6, 7] },
  medio: { mcp: [0, 9, 10], pip: [9, 10, 11] },
  anelar: { mcp: [0, 13, 14], pip: [13, 14, 15] },
  minimo: { mcp: [0, 17, 18], pip: [17, 18, 19] },
};

const CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
];

function angle(a: Pt, b: Pt, c: Pt): number {
  const rad = Math.atan2(c[1] - b[1], c[0] - b[0]) - Math.atan2(a[1] - b[1], a[0] - b[0]);
  let deg = Math.abs((rad * 180) / Math.PI);
  if (deg > 180) deg = 360 - deg;
  return deg;
}

/** Converte os 21 pontos da mão em abertura 0..1 por dedo, com as mesmas fórmulas do desktop. */
export function landmarksToOpenness(lms: NormalizedLandmark[], w: number, h: number): Openness {
  const p: Pt[] = lms.map((l) => [l.x * w, l.y * h]);
  const out = {} as Openness;
  for (const [name, idx] of Object.entries(INDICES) as [Exclude<Finger, 'polegar'>, (typeof INDICES)['medio']][]) {
    const mcp = angle(p[idx.mcp[0]], p[idx.mcp[1]], p[idx.mcp[2]]);
    const pip = angle(p[idx.pip[0]], p[idx.pip[1]], p[idx.pip[2]]);
    const avg = mcp * 0.3 + pip * 0.7;
    out[name] = clamp01((avg - 60) / 120); // 60°-180° -> 0-1 (mapear_angulo_para_servo)
  }
  const palm = Math.hypot(p[5][0] - p[0][0], p[5][1] - p[0][1]);
  const thumb = Math.hypot(p[17][0] - p[4][0], p[17][1] - p[4][1]);
  const ratio = palm > 0 ? thumb / palm : 1;
  out.polegar = clamp01((ratio - 0.5) / 0.8);
  return out;
}

export interface CameraFrame {
  openness: Openness | null;
  confidence: number;
}

export class CameraTracker {
  private landmarker: HandLandmarker | null = null;
  private stream: MediaStream | null = null;
  private raf = 0;
  private lastTs = -1;
  private filters = Object.fromEntries(FINGERS.map((f) => [f, new KalmanFilter(0.2, 5.0, 1.0)])) as Record<Finger, KalmanFilter>;
  private fpsTimes: number[] = [];
  fps = 0;

  constructor(
    private video: HTMLVideoElement,
    private overlay: HTMLCanvasElement,
    private onFrame: (f: CameraFrame) => void,
  ) {}

  get running() {
    return this.stream !== null;
  }

  async init(): Promise<void> {
    if (this.landmarker) return;
    const base = import.meta.env.BASE_URL;
    const fileset = await FilesetResolver.forVisionTasks(`${base}mediapipe`);
    const opts = (delegate: 'GPU' | 'CPU') => ({
      baseOptions: { modelAssetPath: `${base}models/hand_landmarker.task`, delegate },
      runningMode: 'VIDEO' as const,
      numHands: 1,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    try {
      this.landmarker = await HandLandmarker.createFromOptions(fileset, opts('GPU'));
    } catch {
      this.landmarker = await HandLandmarker.createFromOptions(fileset, opts('CPU'));
    }
  }

  static async listCameras(): Promise<MediaDeviceInfo[]> {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.filter((d) => d.kind === 'videoinput');
  }

  async start(deviceId?: string): Promise<void> {
    await this.init();
    this.stop();
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: deviceId ? { deviceId: { exact: deviceId }, width: 640, height: 480 } : { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    });
    this.video.srcObject = this.stream;
    await this.video.play();
    this.loop();
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.video.srcObject = null;
    const ctx = this.overlay.getContext('2d');
    ctx?.clearRect(0, 0, this.overlay.width, this.overlay.height);
    this.fps = 0;
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    const v = this.video;
    if (!this.landmarker || v.readyState < 2) return;
    const ts = performance.now();
    if (ts <= this.lastTs) return;
    this.lastTs = ts;

    const res = this.landmarker.detectForVideo(v, ts);
    this.tickFps(ts);

    const w = v.videoWidth;
    const h = v.videoHeight;
    if (this.overlay.width !== w) this.overlay.width = w;
    if (this.overlay.height !== h) this.overlay.height = h;
    const ctx = this.overlay.getContext('2d')!;
    ctx.clearRect(0, 0, w, h);

    const lms = res.landmarks?.[0];
    if (!lms) {
      this.onFrame({ openness: null, confidence: 0 });
      return;
    }
    this.draw(ctx, lms, w, h);
    const raw = landmarksToOpenness(lms, w, h);
    const filtered = {} as Openness;
    for (const f of FINGERS) filtered[f] = clamp01(this.filters[f].update(raw[f]));
    const conf = Math.round((res.handedness?.[0]?.[0]?.score ?? 0) * 100);
    this.onFrame({ openness: filtered, confidence: conf });
  };

  private tickFps(ts: number) {
    this.fpsTimes.push(ts);
    if (this.fpsTimes.length > 20) this.fpsTimes.shift();
    if (this.fpsTimes.length > 1) {
      this.fps = ((this.fpsTimes.length - 1) * 1000) / (this.fpsTimes[this.fpsTimes.length - 1] - this.fpsTimes[0]);
    }
  }

  private draw(ctx: CanvasRenderingContext2D, lms: NormalizedLandmark[], w: number, h: number) {
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(255,255,255,0.75)';
    ctx.beginPath();
    for (const [a, b] of CONNECTIONS) {
      ctx.moveTo(lms[a].x * w, lms[a].y * h);
      ctx.lineTo(lms[b].x * w, lms[b].y * h);
    }
    ctx.stroke();
    const tracked = new Set([5, 6, 9, 10, 13, 14, 17, 18]);
    lms.forEach((l, i) => {
      ctx.fillStyle = tracked.has(i) ? '#22c55e' : '#f59e0b';
      ctx.beginPath();
      ctx.arc(l.x * w, l.y * h, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  }
}
