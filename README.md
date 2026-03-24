# 🤖 Mão Robótica Multimodal Pro

Sistema unificado e avançado para controle de uma Mão Robótica através de três interfaces de entrada interativas: **Visão Computacional (Câmera)**, **Luva Sensorial Óptica (5DT)** e **Sensores de Ondas Cerebrais (EEG BrainLink)**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-orange)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.31-green)
![Arduino](https://img.shields.io/badge/Arduino-Uno-teal)

## 🌟 Funcionalidades Principais

- **Painel Centralizado (PySide6)**: Interface gráfica moderna com Tema Claro/Escuro e seleção interativa (ComboBox) de portas USB/Bluetooth.
- **Modo Câmera**: Reconhecimento inteligente das mãos via MediaPipe, gerando gestos exatos ou acompanhamento fluido contínuo (PIP e MCP).
- **Modo Luva Sensorial**: Mapeamento linear-segmentado (*piecewise linear interpolation*) de 15 sensores ópticos para movimentos perfeitamente contínuos e individuais dos 5 dedos em tempo real.
- **Modo Neuro (EEG)**: Abertura e fechamento progressivo e sequencial dos dedos puramente comandado pelas suas ondas cerebrais (Modos de **Atenção** e **Meditação**).
- **Perfis Inteligentes**: Salvamento automático de calibrações da Luva e preferências de usuário de forma invisível via `config.json`.

## 📋 Requisitos de Hardware

- Mão Robótica impulsionada por **5 Servo Motores** (SG90 ou similares).
- **Arduino Uno** ou placa compatível rodando `StandardFirmata`.
- Fonte de alimentação externa de 5V dedicada para os servos.
- **Dispositivos de Entrada**: Webcam (Obrigatório), Tiara NeuroSky/BrainLink (Opcional), Luva 5DT Data Glove Ultra (Opcional).

## 🚀 Como Executar

1. Clone o repositório do projeto.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Carregue o **StandardFirmata** no seu Arduino via Arduino IDE (`Arquivo > Exemplos > Firmata > StandardFirmata`).
4. Execute o hub central:
   ```bash
   python main.py
   ```
5. Selecione suas portas COM no menu suspenso ou deixe o `Detectar Portas` encontrar e mapear o Arduino e a tiara EEG automaticamente!

## 📁 Arquitetura Modular (`src/`)

A base de código foi totalmente reestruturada para máxima performance e baixo acoplamento:

| Diretório | Descrição de Domínio |
|-----------|----------------------|
| `/core` | Central de tráfego de dados (`HubController`) e armazenamento de dados locais (`config_manager.py`). |
| `/inputs` | Classes que rodam em Threads isoladas escutando as entradas (`camera_input`, `eeg_input`, `glove_input`). |
| `/outputs` | Comunicação final com o StandardFirmata / Motores (`arduino_output`). |
| `/processing` | Máquinas de cálculos aritméticos (MediaPipe, Geometria de Dedos). |
| `/ui` | Construção de botões, barras de progresso dinâmicas e janelas Qt. |

## 🔌 Pinagem Padrão do Arduino

A ligação PWM dos servos na mão segue o alinhamento:

| Dedo | Pino |
|------|------|
| Polegar | Pino 10 |
| Indicador | Pino 9 |
| Médio | Pino 8 |
| Anelar | Pino 7 |
| Mínimo | Pino 6 |

---
**Desenvolvido com foco no futuro da robótica assistiva multimodal.**
