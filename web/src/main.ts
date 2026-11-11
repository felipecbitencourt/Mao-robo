import './style.css';
import { CameraTracker } from './camera';
import { EegDevice, eegToOpenness, EEG_MODE_LABELS, type EegMode } from './eeg';
import { allOpen, FINGERS, FINGER_LABELS, gestureId, gestureName, type Openness } from './fingers';
import { FirmataBoard } from './firmata';
import { HandOutput } from './hand-output';
import { drawHand } from './virtual-hand';

type Source = 'camera' | 'eeg' | 'manual';
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const state = {
  source: 'camera' as Source,
  openness: allOpen(),
  handVisible: false,
  manual: allOpen(),
  eegMode: 'meditation' as EegMode,
};

// ---------- Saída: barras, mão virtual e Arduino ----------
const bars = $('bars');
const barEls = {} as Record<(typeof FINGERS)[number], { fill: HTMLElement; out: HTMLOutputElement }>;
for (const f of FINGERS) {
  const row = document.createElement('div');
  row.className = 'bar';
  row.innerHTML = `<span>${FINGER_LABELS[f]}</span><div class="track"><div class="fill"></div></div><output></output>`;
  bars.append(row);
  barEls[f] = { fill: row.querySelector('.fill')!, out: row.querySelector('output')! };
}

const handCanvas = $<HTMLCanvasElement>('hand');
const css = getComputedStyle(document.documentElement);
const handColors = () => ({
  skin: css.getPropertyValue('--skin').trim(),
  edge: css.getPropertyValue('--skin-edge').trim(),
  joint: css.getPropertyValue('--joint').trim(),
});

const output = new HandOutput();

function setOpenness(o: Openness | null) {
  state.handVisible = o !== null;
  if (o) state.openness = o;
  const label = state.source === 'camera' && !o ? gestureName(null) : gestureName(gestureId(state.openness));
  $('gesture').textContent = label;
  for (const f of FINGERS) {
    const pct = Math.round(state.openness[f] * 100);
    barEls[f].fill.style.width = `${pct}%`;
    barEls[f].out.textContent = `${pct}%`;
  }
}

function render() {
  drawHand(handCanvas, state.openness, handColors());
  requestAnimationFrame(render);
}
requestAnimationFrame(render);
setOpenness(allOpen());

// ---------- Abas de entrada ----------
const sourceLabels: Record<Source, string> = { camera: 'Câmera', eeg: 'EEG', manual: 'Manual' };
document.querySelectorAll<HTMLButtonElement>('.tabs button').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.source = btn.dataset.src as Source;
    document.querySelectorAll<HTMLButtonElement>('.tabs button').forEach((b) => b.setAttribute('aria-selected', String(b === btn)));
    document.querySelectorAll<HTMLElement>('.panel').forEach((p) => (p.hidden = p.dataset.panel !== state.source));
    $('source-label').textContent = sourceLabels[state.source];
    if (state.source === 'manual') setOpenness({ ...state.manual });
  });
});

// ---------- Câmera ----------
const video = $<HTMLVideoElement>('video');
const camSelect = $<HTMLSelectElement>('camera-select');
const camStatus = $('camera-status');
const tracker = new CameraTracker(video, $<HTMLCanvasElement>('overlay'), (fr) => {
  if (state.source !== 'camera') return;
  setOpenness(fr.openness);
  camStatus.textContent = `${Math.round(tracker.fps)} fps${fr.openness ? ` · confiança ${fr.confidence}%` : ''}`;
});

async function fillCameras() {
  const cams = await CameraTracker.listCameras();
  const current = camSelect.value;
  camSelect.innerHTML = '';
  cams.forEach((c, i) => {
    const opt = new Option(c.label || `Câmera ${i + 1}`, c.deviceId);
    camSelect.add(opt);
  });
  if (current) camSelect.value = current;
  camSelect.hidden = cams.length < 2;
}

async function startCamera() {
  const btn = $<HTMLButtonElement>('btn-camera');
  btn.disabled = true;
  btn.textContent = 'Carregando modelo…';
  try {
    await tracker.start(camSelect.value || undefined);
    $('video-empty').hidden = true;
    $<HTMLButtonElement>('btn-camera-stop').disabled = false;
    await fillCameras();
  } catch (e) {
    camStatus.textContent = `Não foi possível ligar a câmera: ${(e as Error).message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Ligar câmera';
  }
}
$('btn-camera').addEventListener('click', startCamera);
$('btn-camera-stop').addEventListener('click', () => {
  tracker.stop();
  $('video-empty').hidden = false;
  $<HTMLButtonElement>('btn-camera-stop').disabled = true;
  camStatus.textContent = '';
  if (state.source === 'camera') setOpenness(null);
});
camSelect.addEventListener('change', () => {
  if (tracker.running) void startCamera();
});
void fillCameras().catch(() => (camSelect.hidden = true));

function serialError(err: Error, device: string): string {
  if (err.name === 'NotFoundError') return 'Nenhuma porta escolhida.';
  if (err.name === 'InvalidStateError' || /Failed to open serial port/i.test(err.message)) {
    return `Não foi possível abrir a porta d${device}. Ela provavelmente já está em uso por outro programa (app desktop da mão, Monitor Serial do Arduino IDE ou outra aba deste site). Feche-o, reconecte o cabo USB e tente de novo.`;
  }
  return `Falha ao conectar: ${err.message}`;
}

// ---------- Arduino ----------
const pillArduino = $('pill-arduino');
const arduinoStatus = $('arduino-status');
const btnArduino = $<HTMLButtonElement>('btn-arduino');
const btnTest = $<HTMLButtonElement>('btn-test');

function arduinoUi(connected: boolean) {
  pillArduino.classList.toggle('on', connected);
  btnArduino.textContent = connected ? 'Desconectar' : 'Conectar Arduino';
  btnTest.disabled = !connected;
}
output.board.onDisconnect = () => {
  arduinoUi(false);
  arduinoStatus.textContent = 'Arduino desconectado.';
};
async function connectArduino(showAll: boolean) {
  if (output.board.connected) {
    await output.disconnect();
    if (!showAll) return;
  }
  btnArduino.disabled = true;
  arduinoStatus.textContent = 'Escolha a porta do Arduino na janela do navegador…';
  try {
    await output.connect(showAll);
    arduinoUi(true);
    const fw = output.board.firmware ? `, ${output.board.firmware}` : '';
    arduinoStatus.textContent = `Conectado (${output.board.portLabel}${fw}).`;
  } catch (e) {
    const err = e as Error;
    arduinoStatus.textContent =
      err.name === 'NotFoundError' && !showAll
        ? 'Nenhuma porta escolhida. Se o Arduino não apareceu na lista, confira o cabo USB ou use "Outra porta…".'
        : serialError(err, 'o Arduino');
    await output.disconnect();
  } finally {
    btnArduino.disabled = false;
  }
}
btnArduino.addEventListener('click', () => void connectArduino(false));
$('btn-arduino-all').addEventListener('click', () => void connectArduino(true));
btnTest.addEventListener('click', async () => {
  btnTest.disabled = true;
  await output.testSequence((m) => (arduinoStatus.textContent = m));
  btnTest.disabled = !output.board.connected;
});
$<HTMLInputElement>('chk-active').addEventListener('change', (e) => {
  output.active = (e.target as HTMLInputElement).checked;
});
// Suavização do movimento: opcional, desligada por padrão; lembrada neste navegador.
const chkSmooth = $<HTMLInputElement>('chk-smooth');
try { chkSmooth.checked = localStorage.getItem('mao-suavizar') === '1'; } catch { /* sem storage */ }
output.smooth = chkSmooth.checked;
chkSmooth.addEventListener('change', () => {
  output.smooth = chkSmooth.checked;
  try { localStorage.setItem('mao-suavizar', chkSmooth.checked ? '1' : '0'); } catch { /* sem storage */ }
});

// ---------- EEG ----------
const pillEeg = $('pill-eeg');
const btnEeg = $<HTMLButtonElement>('btn-eeg');
const eegModeSel = $<HTMLSelectElement>('eeg-mode');
for (const [k, v] of Object.entries(EEG_MODE_LABELS)) eegModeSel.add(new Option(v, k));
eegModeSel.value = state.eegMode;
eegModeSel.addEventListener('change', () => (state.eegMode = eegModeSel.value as EegMode));

const eeg = new EegDevice(
  (d) => {
    $('eeg-signal').textContent = d.signal === 0 ? 'ótimo' : d.signal >= 200 ? 'sem contato' : String(d.signal);
    $('eeg-att').textContent = String(Math.round(d.value.attention));
    $('eeg-med').textContent = String(Math.round(d.value.meditation));
    $('eeg-foco').textContent = String(Math.round(d.value.foco_real));
    if (state.source === 'eeg' && d.signal < 50) setOpenness(eegToOpenness(state.eegMode, d.value[state.eegMode]));
  },
  () => {
    pillEeg.classList.remove('on');
    btnEeg.textContent = 'Conectar tiara';
  },
);
btnEeg.addEventListener('click', async () => {
  if (eeg.connected) {
    await eeg.disconnect();
    return;
  }
  try {
    await eeg.connect();
    $('eeg-status').textContent = 'Conectada. Aguardando sinal…';
    pillEeg.classList.add('on');
    btnEeg.textContent = 'Desconectar tiara';
  } catch (e) {
    const err = e as Error;
    $('eeg-status').textContent = serialError(err, 'a tiara');
  }
});
const gain = $<HTMLInputElement>('eeg-gain');
gain.addEventListener('input', () => {
  eeg.gain = Number(gain.value);
  $('eeg-gain-out').textContent = gain.value;
});

// ---------- Manual ----------
const sliders = $('manual-sliders');
for (const f of FINGERS) {
  const label = document.createElement('label');
  label.innerHTML = `<span>${FINGER_LABELS[f]}</span><input type="range" min="0" max="100" value="100" data-f="${f}"><output>100%</output>`;
  sliders.append(label);
  const input = label.querySelector('input')!;
  input.addEventListener('input', () => {
    state.manual[f] = Number(input.value) / 100;
    label.querySelector('output')!.textContent = `${input.value}%`;
    if (state.source === 'manual') setOpenness({ ...state.manual });
  });
}
function setAllManual(v: number) {
  sliders.querySelectorAll('label').forEach((l) => {
    const input = l.querySelector('input')!;
    input.value = String(v * 100);
    l.querySelector('output')!.textContent = `${v * 100}%`;
    state.manual[input.dataset.f as (typeof FINGERS)[number]] = v;
  });
  setOpenness({ ...state.manual });
}
$('btn-open').addEventListener('click', () => setAllManual(1));
$('btn-close').addEventListener('click', () => setAllManual(0));
// Envia a pose atual aos servos a ~30 Hz (com "Suavizar movimento" ligado, o lerp do HandOutput deixa o movimento mais lento).
// Sem mão na câmera, a mão robótica fica parada na última pose.
setInterval(() => {
  if (state.source !== 'camera' || state.handVisible) void output.update(state.openness);
}, 33);

// ---------- Suporte do navegador ----------
if (!FirmataBoard.supported) {
  $('serial-warning').hidden = false;
  btnArduino.disabled = true;
  $<HTMLButtonElement>('btn-arduino-all').disabled = true;
  btnEeg.disabled = true;
}
