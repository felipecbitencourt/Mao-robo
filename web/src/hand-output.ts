// Saída para a mão robótica (porte de src/outputs/arduino_output.py).
import { FirmataBoard } from './firmata';
import { FINGERS, type Finger, type Openness } from './fingers';

export const PINS: Record<Finger, number> = { polegar: 10, indicador: 9, medio: 8, anelar: 7, minimo: 6 };
/** Ângulo do servo com o dedo totalmente fechado (VALORES_FECHADOS). */
export const CLOSED_ANGLE: Record<Finger, number> = { polegar: 150, indicador: 180, medio: 160, anelar: 180, minimo: 130 };

export class HandOutput {
  readonly board = new FirmataBoard();
  active = true;
  private pos: Record<Finger, number> = { polegar: 0, indicador: 0, medio: 0, anelar: 0, minimo: 0 };
  private busy = false;

  async connect(showAll = false): Promise<void> {
    await this.board.connect(showAll);
    for (const f of FINGERS) await this.board.servoConfig(PINS[f]);
    for (const f of FINGERS) await this.board.servoWrite(PINS[f], 0);
    this.pos = { polegar: 0, indicador: 0, medio: 0, anelar: 0, minimo: 0 };
  }

  /** Alvo do servo para uma abertura 0..1: aberto = 0°, fechado = CLOSED_ANGLE. */
  static target(f: Finger, openness: number): number {
    return CLOSED_ANGLE[f] * (1 - openness);
  }

  /** Move suavemente em direção ao alvo (lerp 0.3, como mover_servo_suave). */
  async update(o: Openness): Promise<void> {
    if (!this.board.connected || !this.active || this.busy) return;
    this.busy = true;
    try {
      for (const f of FINGERS) {
        const target = HandOutput.target(f, o[f]);
        const diff = target - this.pos[f];
        // lerp 0.3; perto do alvo anda 1° por vez para não parar 1° antes (arredondamento)
        let next = Math.round(this.pos[f] + diff * 0.3);
        if (next === this.pos[f] && Math.abs(diff) >= 1) next = this.pos[f] + Math.sign(diff);
        if (Math.abs(next - this.pos[f]) >= 1) {
          await this.board.servoWrite(PINS[f], next);
          this.pos[f] = next;
        }
      }
    } finally {
      this.busy = false;
    }
  }

  /** Sequência de teste do desktop: abre tudo e fecha/abre um dedo de cada vez. */
  async testSequence(onStep?: (msg: string) => void): Promise<void> {
    if (!this.board.connected) return;
    const wasActive = this.active;
    this.active = false;
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
    for (const f of FINGERS) await this.board.servoWrite(PINS[f], 0);
    await wait(1000);
    for (const f of FINGERS) {
      onStep?.(`Testando ${f}…`);
      await this.board.servoWrite(PINS[f], CLOSED_ANGLE[f]);
      await wait(1000);
      await this.board.servoWrite(PINS[f], 0);
      await wait(1000);
    }
    this.pos = { polegar: 0, indicador: 0, medio: 0, anelar: 0, minimo: 0 };
    this.active = wasActive;
    onStep?.('Teste finalizado');
  }

  disconnect() {
    return this.board.disconnect();
  }
}
