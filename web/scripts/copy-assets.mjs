// Copia o runtime WASM do MediaPipe e o modelo da mão para public/,
// para que o site sirva tudo do próprio domínio (sem CDN externo).
import { cpSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const pub = join(root, 'public');

mkdirSync(join(pub, 'mediapipe'), { recursive: true });
mkdirSync(join(pub, 'models'), { recursive: true });

cpSync(join(root, 'node_modules/@mediapipe/tasks-vision/wasm'), join(pub, 'mediapipe'), { recursive: true });
cpSync(join(root, '../models/hand_landmarker.task'), join(pub, 'models/hand_landmarker.task'));
console.log('assets: wasm do MediaPipe e hand_landmarker.task copiados para public/');
