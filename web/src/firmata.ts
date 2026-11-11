// Cliente Firmata mínimo sobre Web Serial: só o que a mão precisa (servos).
// O Arduino continua rodando o StandardFirmata, exatamente como no app desktop (pyfirmata).

const SET_PIN_MODE = 0xf4;
const ANALOG_MESSAGE = 0xe0;
const START_SYSEX = 0xf0;
const END_SYSEX = 0xf7;
const SERVO_CONFIG = 0x70;
const EXTENDED_ANALOG = 0x6f;
const REPORT_FIRMWARE = 0x79;
const PIN_MODE_SERVO = 0x04;

export class FirmataBoard {
  private port: SerialPort | null = null;
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  firmware = '';
  onDisconnect: (() => void) | null = null;

  static get supported(): boolean {
    return 'serial' in navigator;
  }

  get connected() {
    return this.writer !== null;
  }

  /** Abre o seletor de portas do navegador e conecta (57600 baud, padrão do StandardFirmata). */
  async connect(baudRate = 57600): Promise<void> {
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate });
    this.port = port;
    this.writer = port.writable!.getWriter();
    navigator.serial.addEventListener('disconnect', this.handleDisconnect);
    // Abrir a serial reinicia o Arduino; esperamos o relatório de firmware (ou 3 s).
    await Promise.race([this.readUntilFirmware(), new Promise((r) => setTimeout(r, 3000))]);
    if (!this.firmware) await this.send([START_SYSEX, REPORT_FIRMWARE, END_SYSEX]);
  }

  private handleDisconnect = (e: Event) => {
    if ((e.target as SerialPort) === this.port || (e as unknown as { port?: SerialPort }).port === this.port) {
      void this.disconnect();
    }
  };

  private async readUntilFirmware(): Promise<void> {
    if (!this.port?.readable) return;
    this.reader = this.port.readable.getReader();
    const buf: number[] = [];
    const reader = this.reader;
    // Continua lendo em segundo plano para não encher o buffer da porta.
    (async () => {
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          if (!value) continue;
          for (const b of value) {
            buf.push(b);
            if (b === END_SYSEX) {
              const start = buf.lastIndexOf(START_SYSEX);
              if (start >= 0 && buf[start + 1] === REPORT_FIRMWARE) {
                const nameBytes = buf.slice(start + 4, buf.length - 1);
                let name = '';
                for (let i = 0; i + 1 < nameBytes.length; i += 2) name += String.fromCharCode(nameBytes[i] | (nameBytes[i + 1] << 7));
                this.firmware = `${name} v${buf[start + 2]}.${buf[start + 3]}`;
              }
              buf.length = 0;
            }
            if (buf.length > 512) buf.length = 0;
          }
        }
      } catch {
        /* porta fechada */
      }
    })();
    const t0 = performance.now();
    while (!this.firmware && performance.now() - t0 < 3000) await new Promise((r) => setTimeout(r, 50));
  }

  private async send(bytes: number[]): Promise<void> {
    if (!this.writer) return;
    try {
      await this.writer.write(new Uint8Array(bytes));
    } catch {
      await this.disconnect();
    }
  }

  /** Equivale a board.digital[pin].mode = SERVO no pyfirmata (pulso 544-2400 µs). */
  async servoConfig(pin: number, minPulse = 544, maxPulse = 2400): Promise<void> {
    await this.send([
      START_SYSEX, SERVO_CONFIG, pin,
      minPulse & 0x7f, (minPulse >> 7) & 0x7f,
      maxPulse & 0x7f, (maxPulse >> 7) & 0x7f,
      END_SYSEX,
    ]);
    await this.send([SET_PIN_MODE, pin, PIN_MODE_SERVO]);
  }

  /** Equivale a board.digital[pin].write(angulo). */
  async servoWrite(pin: number, angle: number): Promise<void> {
    const v = Math.max(0, Math.min(180, Math.round(angle)));
    if (pin < 16) {
      await this.send([ANALOG_MESSAGE | pin, v & 0x7f, (v >> 7) & 0x7f]);
    } else {
      await this.send([START_SYSEX, EXTENDED_ANALOG, pin, v & 0x7f, (v >> 7) & 0x7f, END_SYSEX]);
    }
  }

  async disconnect(): Promise<void> {
    navigator.serial?.removeEventListener('disconnect', this.handleDisconnect);
    const port = this.port;
    this.port = null;
    try { await this.reader?.cancel(); } catch { /* ignore */ }
    try { this.reader?.releaseLock(); } catch { /* ignore */ }
    try { this.writer?.releaseLock(); } catch { /* ignore */ }
    this.reader = null;
    const hadWriter = this.writer !== null;
    this.writer = null;
    try { await port?.close(); } catch { /* ignore */ }
    this.firmware = '';
    if (hadWriter) this.onDisconnect?.();
  }
}
