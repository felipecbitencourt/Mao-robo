# Mão Robótica — versão web

Versão para navegador do app desktop, publicada em **https://mao.cienciaberta.com**.
É um site estático: tudo roda no navegador de quem abre a página, sem servidor.

| Recurso | Como funciona na web | Equivale no desktop a |
|---|---|---|
| Câmera | MediaPipe Tasks Vision (JS/WASM) com o mesmo `models/hand_landmarker.task` | `src/processing/hand_processor.py` |
| Arduino | Web Serial falando Firmata (o Arduino continua com o **StandardFirmata**) | `src/outputs/arduino_output.py` (pyfirmata) |
| EEG BrainLink | Web Serial + parser ThinkGear (porta serial criada pelo pareamento Bluetooth) | `src/hardware/eeg_brainlink.py` + `hub_controller.py` |
| Modo manual | Sliders por dedo, útil para testar servos | — |
| Luva 5DT | **Não suportada** (depende da DLL do Windows) | `src/inputs/glove_input.py` |

Web Serial só existe no **Chrome e no Edge para desktop**. Em outros navegadores a câmera e a mão virtual funcionam, mas não dá para conectar o hardware.

## Desenvolvimento

```bash
cd web
npm install
npm run dev      # http://localhost:5173 (localhost conta como contexto seguro para câmera e serial)
npm test         # testes da lógica portada (ângulos, servos, ThinkGear)
npm run build    # gera dist/
```

`npm run dev` e `npm run build` copiam o runtime WASM do MediaPipe e o modelo `../models/hand_landmarker.task` para `public/` antes de rodar, então o site não depende de CDN externo.

## Deploy no Cloudflare

O site é publicado como Worker só com assets estáticos (`wrangler.jsonc`), já apontando para o domínio personalizado `mao.cienciaberta.com`.

**Automático (recomendado):** no painel do Cloudflare, *Workers & Pages → Create → Import a repository*, escolha `felipecbitencourt/Mao-robo` e configure:

- Root directory: `web`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy`

A partir daí cada push na `main` publica sozinho. O domínio `mao.cienciaberta.com` é criado pelo próprio deploy, desde que a zona `cienciaberta.com` esteja na mesma conta Cloudflare.

**Manual:** `npx wrangler login` e depois `npm run deploy`.
