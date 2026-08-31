# 🤖 Mão Robótica Multimodal Pro

Sistema unificado para controle de uma mão robótica através de três interfaces de entrada interativas: **Visão Computacional (Câmera)**, **Luva Sensorial Óptica (5DT)** e **Sensores de Ondas Cerebrais (EEG BrainLink)**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-orange)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Tasks-green)
![Arduino](https://img.shields.io/badge/Arduino-Uno-teal)

## 🌟 Funcionalidades Principais

- **Painel Centralizado (PySide6)**: interface gráfica com tema claro/escuro e seleção interativa de portas USB/Bluetooth.
- **Modo Câmera**: reconhecimento das mãos via MediaPipe Tasks, gerando gestos discretos ou acompanhamento fluido contínuo por dedo. Suporta **câmera única ou visão dual com fusão** das duas fontes.
- **Modo Luva Sensorial**: mapeamento linear-segmentado (*piecewise linear interpolation*) dos sensores ópticos da 5DT para movimento contínuo e individual dos 5 dedos, com calibração em três estados (`CLOSED` / `HALF` / `OPEN`).
- **Modo Neuro (EEG)**: abertura e fechamento progressivo dos dedos comandado por ondas cerebrais, nos modos **Atenção**, **Meditação** e **Foco Real** (este último usando limiar calibrado por usuário).
- **Perfis Persistentes**: calibrações da luva, limiares clínicos e preferências salvos automaticamente em `config.json`.

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
| `src/utils/` | Utilitários auxiliares de configuração |
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

`config.json` (raiz) guarda o estado da aplicação e é reescrito automaticamente:

| Chave | Função |
|-------|--------|
| `arduino_port`, `eeg_port` | Portas COM dos dispositivos |
| `camera_index`, `camera2_index` | Índices das webcams |
| `camera_backend` | `msmf` ou `dshow` |
| `glove_calibration` | Leituras de referência dos estados `HALF` e `OPEN` |
| `glove_weights` | Ganho individual por dedo |
| `eeg_gain`, `eeg_smoothing` | Sensibilidade e suavização do sinal EEG |
| `theme_dark_mode` | Tema da interface |

`config/calibracao_eeg.json` guarda o limiar de foco calculado no protocolo de calibração (médias de relaxamento e concentração).

## 📦 Gerar o Executável

O empacotamento usa PyInstaller com um `.spec` já configurado (inclui modelos, imagens de gestos e `config.json` como dados estáticos):

```bash
pyinstaller MaoRobotica.spec
```

O resultado sai em `dist/MaoRobotica/`. Essa pasta é ignorada pelo Git.

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

Portas e índice de câmera são lidos do mesmo `config.json` da interface desktop. A tiara EEG é opcional: se não for encontrada, o modo `gestures` continua funcionando.

⚠️ **Escopo do protótipo**: ele apenas *publica telemetria* — o acionamento dos servos nunca foi implementado nesta via. Para mover a mão de verdade, use a interface desktop (`main.py`), que passa por `src/outputs/arduino_output.py`.

## 📚 Documentação Adicional

- [`VISAO_COMPUTACIONAL.md`](VISAO_COMPUTACIONAL.md) — fundamentação técnica do módulo de visão computacional.
- [`src/luva/README.md`](src/luva/README.md) — SDK da luva e projeto de avaliação clínica.

---
**Desenvolvido com foco no futuro da robótica assistiva multimodal.**
