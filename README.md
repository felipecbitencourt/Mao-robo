# 🤖 Mão Robótica - Controle por Gestos e EEG

Sistema de controle de mão robótica usando visão computacional com MediaPipe, ondas cerebrais (EEG) e Arduino.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.15-green)
![EEG](https://img.shields.io/badge/EEG-BrainLink_Pro-purple)
![Arduino](https://img.shields.io/badge/Arduino-Uno-teal)

## 📋 Requisitos

### Hardware
- Arduino Uno (ou compatível)
- 5 Servo motores (SG90 ou similar)
- Fonte de alimentação externa 5V (recomendado para os servos)
- Webcam (para controle por gestos)
- Headset BrainLink Pro (opcional para controle por EEG)

### Software
- Python 3.13+
- Arduino IDE (para upload do StandardFirmata)

## 🚀 Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Carregue o **StandardFirmata** no Arduino:
   - Arduino IDE → Arquivo → Exemplos → Firmata → StandardFirmata
   - Selecione a porta COM correta
   - Upload

## 📁 Estrutura do Projeto

| Arquivo | Descrição |
|---------|-----------|
| `main_fluido_v2.py` | Controle proporcional + multi-ângulo + temporal (Principal) |
| `main_eeg.py` | Controle por ondas cerebrais (Atenção/Concentração) |
| `calibrar_eeg_protocolo.py` | Protocolo interativo de calibração para o EEG |
| `eeg_brainlink.py` | Biblioteca de interface com BrainLink Pro |
| `servo_braco3d.py` | Biblioteca de controle dos servos (Arduino) |
| `launcher.py` | Interface gráfica do sistema |

## 🎮 Modos de Operação

### 1. Modo Gestos (Principal)
Use `main_fluido_v2.py` para controle proporcional suave. A mão robótica imita a posição exata dos seus dedos com alta estabilidade e suavização temporal.

### 2. Modo EEG (Mente)
Use `main_eeg.py` para controlar a mão com a concentração:
- **Concentrado** (Atenção >= Threshold): A mão fecha.
- **Relaxado** (Atenção < Threshold): A mão abre.

## ⚙️ Calibração

### Servos
Os valores de fechamento de cada dedo estão em `servo_braco3d.py`:
```python
VALORES_FECHADOS = {
    10: 150,  # Polegar
    9: 180,   # Indicador
    8: 160,   # Médio
    7: 180,   # Anelar
    6: 130    # Mínimo
}
```

### EEG
Antes de usar o modo cerebral, execute o protocolo de calibração:
```bash
python calibrar_eeg_protocolo.py
```
Isso definirá o seu limite (threshold) pessoal de concentração e salvará em `calibracao_eeg.json`.

## 🔌 Pinagem Arduino

| Dedo | Pino |
|------|------|
| Polegar | 10 |
| Indicador | 9 |
| Médio | 8 |
| Anelar | 7 |
| Mínimo | 6 |

## 📦 Executável

O arquivo `MaoRobotica.exe` na pasta `dist/` (ou rodando `launcher.py`) permite usar o sistema sem instalar Python diretamente.

## 🛠️ Troubleshooting

- **Servos não movem:** Verifique se o StandardFirmata foi carregado no Arduino.
- **Headset não conecta:** Garanta que o BrainLink está pareado via Bluetooth e use a porta COM correta em `main_eeg.py`.
- **Porta COM errada:** Edite `PORTA_COM` nos arquivos Python correspondentes.

---
Desenvolvido com ❤️ usando MediaPipe, PyFirmata e BrainLink EEG
