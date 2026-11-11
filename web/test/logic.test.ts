// Testes rápidos da lógica portada (rodar: npm test)
import assert from 'node:assert/strict';
import { landmarksToOpenness } from '../src/camera';
import { ThinkGearParser, sequentialOpenness } from '../src/eeg';
import { gestureId } from '../src/fingers';
import { HandOutput } from '../src/hand-output';

// Mão aberta sintética: dedos retos para cima, polegar afastado.
const lm = Array.from({ length: 21 }, () => ({ x: 0.5, y: 0.5, z: 0, visibility: 1 }));
const set = (i: number, x: number, y: number) => (lm[i] = { x, y, z: 0, visibility: 1 });
set(0, 0.5, 0.9);
[[5, 0.4], [9, 0.47], [13, 0.54], [17, 0.61]].forEach(([b, x]) => {
  for (let k = 0; k < 4; k++) set(b + k, x, 0.6 - k * 0.08);
});
set(1, 0.4, 0.85); set(2, 0.32, 0.78); set(3, 0.25, 0.72); set(4, 0.18, 0.66);
const open = landmarksToOpenness(lm, 640, 480);
assert.ok(open.indicador > 0.85 && open.minimo > 0.85, 'dedos retos = abertos');
assert.ok(open.polegar > 0.5, 'polegar afastado = aberto');
assert.equal(gestureId(open), 15);

// Dobra o indicador: PIP volta para baixo.
set(7, 0.4, 0.62); set(6, 0.4, 0.52);
set(7, 0.43, 0.6);
const bent = landmarksToOpenness(lm, 640, 480);
assert.ok(bent.indicador < open.indicador, 'indicador dobrado fecha');

// Servo: aberto = 0°, fechado = VALORES_FECHADOS.
assert.equal(HandOutput.target('indicador', 1), 0);
assert.equal(HandOutput.target('polegar', 0), 150);

// EEG sequencial: 50 => polegar e indicador abertos, médio pela metade.
const s = sequentialOpenness(50, false);
assert.deepEqual([s.polegar, s.indicador, s.medio, s.anelar], [1, 1, 0.5, 0]);

// ThinkGear: pacote com sinal=0, atenção=70, meditação=40.
const payload = [0x02, 0x00, 0x04, 70, 0x05, 40];
const sum = payload.reduce((a, b) => a + b, 0) & 0xff;
const pkt = new Uint8Array([0x13, 0xaa, 0xaa, payload.length, ...payload, (~sum) & 0xff]);
const p = new ThinkGearParser();
assert.ok(p.push(pkt));
assert.equal(p.data.attention, 70);
assert.equal(p.data.meditation, 40);
assert.equal(p.data.signal, 0);
console.log('ok: todos os testes passaram');
