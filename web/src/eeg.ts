// Tiara BrainLink / NeuroSky via Web Serial (porte de src/hardware/eeg_brainlink.py e da
// lógica EEG de src/core/hub_controller.py). O pareamento Bluetooth cria uma porta serial
// no sistema (ex.: COM10), que o navegador consegue abrir.
import { FINGERS, type Openness } from './fingers';

export interface EegData {
  signal: number; // 0 = ótimo, 200 = sem contato
  attention: number;
  meditation: number;
  battery: number | null;
  waves: { delta: number; theta: number; lowAlpha: number; highAlpha: number; lowBeta: number; highBeta: number; lowGamma: number; highGamma: number };
}

export type EegMode = 'attention' | 'meditation' | 'foco_real';

export const EEG_MODE_LABELS: Record<EegMode, string> = {
  meditation: 'Meditação abre a mão',
  attention: 'Atenção fecha a mão',
  foco_real: 'Foco real (fração beta) abre a mão',
};

export class ThinkGearParser {
  private buf: number[] = [];
  readonly data: EegData = {
    signal: 200, attention: 0, meditation: 0, battery: null,
    waves: { delta: 0, theta: 0, lowAlpha: 0, highAlpha: 0, lowBeta: 0, highBeta: 0, lowGamma: 0, highGamma: 0 },
  };

  /** Recebe bytes e retorna true se algum pacote válido foi decodificado. */
  push(bytes: Uint8Array): boolean {
    let got = false;
    for (const b of bytes) this.buf.push(b);
    while (this.buf.length >= 4) {
      if (this.buf[0] !== 0xaa || this.buf[1] !== 0xaa) {
        this.buf.shift();
        continue;
      }
      const len = this.buf[2];
      if (len > 169) { this.buf.shift(); continue; }
      const total = 4 + len;
      if (this.buf.length < total) break;
      const payload = this.buf.slice(3, 3 + len);
      const checksum = this.buf[3 + len];
      const sum = payload.reduce((a, v) => a + v, 0) & 0xff;
      if (((~sum) & 0xff) === checksum) {
        this.parsePayload(payload);
        got = true;
      }
      this.buf.splice(0, total);
    }
    return got;
  }

  private parsePayload(p: number[]) {
    let i = 0;
    while (i < p.length) {
      while (i < p.length && p[i] === 0x55) i++;
      if (i >= p.length) break;
      const code = p[i++];
      if (code >= 0x80) {
        const n = p[i++];
        const v = p.slice(i, i + n);
        i += n;
        if (code === 0x83 && v.length >= 24) {
          const r = (k: number) => (v[k] << 16) | (v[k + 1] << 8) | v[k + 2];
          const w = this.data.waves;
          w.delta = r(0); w.theta = r(3); w.lowAlpha = r(6); w.highAlpha = r(9);
          w.lowBeta = r(12); w.highBeta = r(15); w.lowGamma = r(18); w.highGamma = r(21);
        }
      } else {
        const v = p[i++];
        if (code === 0x02) this.data.signal = v;
        else if (code === 0x04) this.data.attention = v;
        else if (code === 0x05) this.data.meditation = v;
        else if (code === 0x01) this.data.battery = v;
      }
    }
  }
}

/** Abertura sequencial dos 5 dedos: cada dedo ocupa uma faixa de 20 pontos (_calculate_eeg_fingers). */
export function sequentialOpenness(val: number, invert: boolean): Openness {
  const out = {} as Openness;
  FINGERS.forEach((f, i) => {
    let perc = Math.max(0, Math.min(1, (val - i * 20) / 20));
    if (invert) perc = 1 - perc;
    out[f] = perc;
  });
  return out;
}

export class EegDevice {
  private port: SerialPort | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private parser = new ThinkGearParser();
  private ema: Record<string, number> = {};
  gain = 5.0;
  smoothing = 0.2;

  constructor(private onData: (d: EegData & { value: Record<EegMode, number> }) => void, private onClose: () => void) {}

  get connected() {
    return this.port !== null;
  }

  async connect(baudRate = 57600): Promise<void> {
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate });
    this.port = port;
    this.parser = new ThinkGearParser();
    void this.readLoop();
  }

  private async readLoop() {
    if (!this.port?.readable) return;
    this.reader = this.port.readable.getReader();
    try {
      for (;;) {
        const { value, done } = await this.reader.read();
        if (done) break;
        if (value && this.parser.push(value)) this.emit();
      }
    } catch {
      /* desconectado */
    } finally {
      await this.disconnect();
    }
  }

  private emit() {
    const d = this.parser.data;
    const amp = (v: number) => Math.max(0, Math.min(100, 50 + (v - 50) * this.gain));
    const w = d.waves;
    const total = w.delta + w.theta + w.lowAlpha + w.highAlpha + w.lowBeta + w.highBeta + w.lowGamma + w.highGamma;
    const rawFoco = Math.min(100, ((w.lowBeta + w.highBeta) / Math.max(1, total)) * 100);
    const prev = this.ema.foco_real ?? rawFoco;
    const foco = prev * this.smoothing + rawFoco * (1 - this.smoothing);
    this.ema.foco_real = foco;
    this.onData({ ...d, value: { attention: amp(d.attention), meditation: amp(d.meditation), foco_real: foco } });
  }

  async disconnect(): Promise<void> {
    if (!this.port) return;
    const port = this.port;
    this.port = null;
    try { await this.reader?.cancel(); } catch { /* ignore */ }
    try { this.reader?.releaseLock(); } catch { /* ignore */ }
    this.reader = null;
    try { await port.close(); } catch { /* ignore */ }
    this.onClose();
  }
}

/** Converte a leitura EEG em abertura dos dedos conforme o modo escolhido. */
export function eegToOpenness(mode: EegMode, value: number): Openness {
  if (mode === 'foco_real') {
    const o = value / 100;
    return { polegar: o, indicador: o, medio: o, anelar: o, minimo: o };
  }
  return sequentialOpenness(value, mode === 'attention');
}
