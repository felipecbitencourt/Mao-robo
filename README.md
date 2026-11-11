# 🤖 Mão Robótica Multimodal Pro

Sistema unificado para controle de uma mão robótica através de três interfaces de entrada interativas: **Visão Computacional (Câmera)**, **Luva Sensorial Óptica (5DT)** e **Sensores de Ondas Cerebrais (EEG BrainLink)**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-orange)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Tasks-green)
![Arduino](https://img.shields.io/badge/Arduino-Uno-teal)

## 🌟 Funcionalidades Principais

- **Painel Centralizado (PySide6)**: interface gráfica com tema claro/escuro e seleção interativa de portas USB/Bluetooth.
- **Modo Câmera**: reconhecimento das mãos via MediaPipe Tasks, gerando gestos discretos ou acompanhamento fluido contínuo por dedo. Suporta **câmera única ou visão dual com fusão** das duas fontes.
- **Modo Luva Sensorial**: cada dedo do robô segue os dois sensores de flexão do dedo correspondente na 5DT (articulação próxima e distante). Sem calibração, o movimento é contínuo (com ganho por dedo). Com a calibração clínica (10 ciclos abrir/fechar), cada dedo abre ou fecha conforme o limiar.
- **Modo Neuro (EEG)**: abertura e fechamento progressivo dos dedos comandado por ondas cerebrais, nos modos **Atenção**, **Meditação** e **Foco Real** (este último usando limiar calibrado por usuário).
- **Perfis Persistentes**: calibrações da luva, limiares clínicos e preferências salvos automaticamente em `config.local.json`.
- **Gravação de sessão**: a chave "Gravar sessão (CSV)" grava cada predição (fonte, gesto, confiança e abertura de cada dedo) em `gravacoes/`.
- **Parada de emergência**: o botão "Parar motores" (ou Esc) leva todos os servos à posição de mão aberta e desliga as entradas.

## 📋 Requisitos de Hardware

- Mão robótica acionada por **5 servomotores** (SG90 ou similares).
- **Arduino Uno** ou placa compatível rodando `StandardFirmata`.
- Fonte de alimentação externa de 5 V dedicada para os servos.
- **Entradas**: webcam (obrigatório), tiara NeuroSky/BrainLink (opcional), luva 5DT Data Glove Ultra (opcional).

## ⚙️ Instalação

```bash
pip install -r requirements.txt
```

Depois, carregue o **StandardFirmata** no Arduino pela Arduino IDE (`Arquivo > Exemplos > Firmata > StandardFirmata`).

## 🚀 Como Executar

```bash
python main.py
```

Selecione as portas COM no menu suspenso, ou use o botão **Detectar Portas** para mapear o Arduino e a tiara EEG automaticamente.

Se precisar identificar portas fora da interface, existe um utilitário de linha de comando:

```bash
python detect_ports.py
```

## 🎛️ Modos de Entrada

| Modo | Fonte | Observações |
|------|-------|-------------|
| `CAMERA 1` | Webcam principal | Modo padrão, menor latência |
| `CAMERA 2` | Webcam secundária | Requer `camera2_index` configurado |
| `VISÃO DUAL (FUSÃO)` | Ambas as câmeras | Combina as duas estimativas para reduzir oclusão |
| Luva 5DT | Sensores ópticos | Exige calibração prévia dos três estados |
| EEG | BrainLink | `attention`, `meditation` e `foco_real` |

O detalhamento técnico do pipeline de visão (aquisição, inferência de landmarks e orquestração) está em [`VISAO_COMPUTACIONAL.md`](VISAO_COMPUTACIONAL.md).

## 📁 Estrutura do Projeto

| Caminho | Descrição |
|---------|-----------|
| `main.py` | Ponto de entrada; insere `src/` no `sys.path` e sobe a janela Qt |
| `src/core/` | Central de tráfego de dados (`HubController`) e persistência (`config_manager`, `paths`) |
| `src/inputs/` | Threads isoladas de captura (`camera_input`, `eeg_input`, `glove_input`) |
| `src/processing/` | Cálculo de landmarks e geometria dos dedos (`hand_processor`, `classifier`) |
| `src/outputs/` | Comunicação com StandardFirmata e servos (`arduino_output`) |
| `src/hardware/` | Driver de baixo nível do BrainLink (`eeg_brainlink`) |
| `src/ui/` | Janela principal e componentes Qt reutilizáveis |
| `src/processing/finger_scale.py` | Escala única dos dedos (abertura 0 a 1) e mapa dos 18 sensores da luva |
| `tests/` | Testes que rodam sem hardware (`pytest`) |
| `src/luva/` | SDK 5DT Data Glove Ultra, assets 3D e projeto de avaliação clínica |
| `models/` | Modelos MediaPipe (`hand_landmarker.task`, `gesture_recognizer.task`) |
| `config/` | Calibração de EEG por usuário |
| `lixeira/` | Versões antigas dos scripts, mantidas por referência histórica. **Não faz parte da aplicação.** |

> Os módulos usam imports absolutos (`from core.hub_controller import ...`) porque `src/` é adicionado ao `sys.path` em tempo de execução. Ao rodar scripts avulsos, faça o mesmo.

## 🔌 Pinagem Padrão do Arduino

| Dedo | Pino |
|------|------|
| Polegar | 10 |
| Indicador | 9 |
| Médio | 8 |
| Anelar | 7 |
| Mínimo | 6 |

## 🗃️ Configuração

`config.json` (raiz, versionado) traz os valores padrão. O estado desta máquina fica em `config.local.json`, que é ignorado pelo git e gravado de forma atômica. Na primeira execução ele é criado a partir do `config.json` atual, então calibrações antigas são mantidas. Chaves:

| Chave | Função |
|-------|--------|
| `arduino_port`, `eeg_port` | Portas COM dos dispositivos |
| `camera_index`, `camera2_index` | Índices das webcams |
| `camera_backend` | `msmf` ou `dshow` |
| `glove_calibration` | Leituras de referência dos estados `HALF` e `OPEN` |
| `glove_clinical_thresholds` | Limiar por sensor da calibração clínica (valor ≥ limiar = dedo fechado) |
| `glove_weights` | Ganho individual por dedo |
| `eeg_gain`, `eeg_smoothing` | Sensibilidade e suavização do sinal EEG |
| `theme_dark_mode` | Tema da interface |

`config/calibracao_eeg.json` guarda o limiar de foco calculado no protocolo de calibração (médias de relaxamento e concentração).

## 🧪 Testes

Os testes cobrem o que dá para verificar sem hardware: escala dos dedos e mapa da luva, parser do BrainLink, saída para o Arduino (com placa simulada), fusão das câmeras, configuração e gravação em CSV.

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## 📦 Gerar o Executável

O empacotamento usa PyInstaller com um `.spec` já configurado (inclui modelos, imagens de gestos e `config.json` como dados estáticos):

```bash
pyinstaller MaoRobotica.spec
```

O resultado sai em `dist/MaoRobotica/`. Essa pasta é ignorada pelo Git.

## 🌐 Versão Web (mao.cienciaberta.com)

A pasta `web/` tem uma versão que roda inteira no navegador, sem instalar nada: câmera com MediaPipe JS, Arduino e tiara EEG por Web Serial (Chrome/Edge no computador) e uma mão virtual para quem não tem o hardware. O Arduino usa o mesmo StandardFirmata. Detalhes e deploy no Cloudflare em [`web/README.md`](web/README.md).

## 🧪 Interface Web (protótipo)

O repositório contém um protótipo de front-end React/Vite (`frontend/`) alimentado por um servidor FastAPI (`server.py`), que publica telemetria por WebSocket.

```bash
python server.py
```

```bash
cd frontend
npm install
npm run dev
```

O servidor sobe em `http://localhost:8000` e expõe:

| Rota | Tipo | Função |
|------|------|--------|
| `/ws` | WebSocket | Telemetria contínua (mão detectada, ângulos por dedo, métricas de EEG) |
| `/set_mode` | POST | Alterna entre os modos `gestures` e `eeg` |

Portas e índice de câmera são lidos da mesma configuração da interface desktop (`config.json` + `config.local.json`). A tiara EEG é opcional: se não for encontrada, o modo `gestures` continua funcionando.

⚠️ **Escopo do protótipo**: ele apenas *publica telemetria* — o acionamento dos servos nunca foi implementado nesta via. Para mover a mão de verdade, use a interface desktop (`main.py`), que passa por `src/outputs/arduino_output.py`.

## 📚 Documentação Adicional

- [`VISAO_COMPUTACIONAL.md`](VISAO_COMPUTACIONAL.md) — fundamentação técnica do módulo de visão computacional.
- [`src/luva/README.md`](src/luva/README.md) — SDK da luva e projeto de avaliação clínica.

---
**Desenvolvido com foco no futuro da robótica assistiva multimodal.**
