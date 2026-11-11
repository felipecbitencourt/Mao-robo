// Representação comum da mão: abertura de cada dedo de 0 (fechado) a 1 (aberto).
// Todas as entradas (câmera, EEG, sliders) produzem isso; a saída (Arduino, mão virtual) consome.

export const FINGERS = ['polegar', 'indicador', 'medio', 'anelar', 'minimo'] as const;
export type Finger = (typeof FINGERS)[number];
export type Openness = Record<Finger, number>;

export const FINGER_LABELS: Record<Finger, string> = {
  polegar: 'Polegar',
  indicador: 'Indicador',
  medio: 'Médio',
  anelar: 'Anelar',
  minimo: 'Mínimo',
};

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export const allOpen = (): Openness => ({ polegar: 1, indicador: 1, medio: 1, anelar: 1, minimo: 1 });

/** Filtro de Kalman 1D (mesmo do hand_processor.py). */
export class KalmanFilter {
  private p: number;
  constructor(private q = 0.2, private r = 5.0, private x = 1.0, e = 1.0) {
    this.p = e;
  }
  update(measurement: number): number {
    this.p += this.q;
    const k = this.p / (this.p + this.r);
    this.x += k * (measurement - this.x);
    this.p *= 1 - k;
    return this.x;
  }
}

/** ID de gesto 0-15 (bits: indicador, médio, anelar, mínimo), como no app desktop. */
export function gestureId(o: Openness): number {
  // No desktop um dedo conta como "levantado" quando o ângulo médio passa de 125°,
  // o que equivale a abertura (125-60)/120 ≈ 0.54.
  const t = 0.54;
  return (o.indicador > t ? 1 : 0) + (o.medio > t ? 2 : 0) + (o.anelar > t ? 4 : 0) + (o.minimo > t ? 8 : 0);
}

export function gestureName(id: number | null): string {
  if (id === null) return 'Sem mão';
  if (id === 15) return 'Mão aberta';
  if (id === 0) return 'Punho fechado';
  return `Gesto ${id}`;
}
