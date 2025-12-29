# 🤖 Mão Robótica - Controle por Gestos

Sistema de controle de mão robótica usando visão computacional com MediaPipe e Arduino.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.31-green)
![Arduino](https://img.shields.io/badge/Arduino-Uno-teal)

## 📋 Requisitos

### Hardware
- Arduino Uno (ou compatível)
- 5 Servo motores (SG90 ou similar)
- Fonte de alimentação externa 5V (recomendado para os servos)
- Webcam

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
| `main.py` | Controle por gestos (IA híbrida) |
| `main_fluido.py` | Controle proporcional suave |
| `main_fluido_v2.py` | Controle proporcional + multi-ângulo + temporal |
| `testar-dedos.py` | Teste de calibração dos servos |
| `servo_braco3d.py` | Biblioteca de controle dos servos |
| `launcher.py` | Interface gráfica do executável |

## 🎮 Modos de Operação

### 1. Modo Gestos (`main.py`)
Reconhece gestos completos usando IA:
- ✊ Punho fechado
- ✋ Palma aberta  
- ✌️ Vitória
- 👍 Joinha
- 🤘 Rock

### 2. Modo Fluido (`main_fluido.py`)
Controle proporcional - a mão robótica imita a posição exata dos seus dedos.

### 3. Modo Fluido V2 (`main_fluido_v2.py`)
Versão aprimorada com:
- 2 ângulos por dedo (MCP + PIP)
- Média temporal de 5 frames
- Maior estabilidade

## ⚙️ Calibração

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

Use `testar-dedos.py` para encontrar os valores ideais.

## 🔌 Pinagem Arduino

| Dedo | Pino |
|------|------|
| Polegar | 10 |
| Indicador | 9 |
| Médio | 8 |
| Anelar | 7 |
| Mínimo | 6 |

## 📦 Executável

O arquivo `MaoRobotica.exe` na pasta `dist/` permite usar o sistema sem instalar Python.

## 🛠️ Troubleshooting

- **Servos não movem:** Verifique se o StandardFirmata foi carregado no Arduino
- **Porta COM errada:** Edite `PORTA_COM` nos arquivos Python
- **Movimentos instáveis:** Use o Modo Fluido V2 para maior estabilidade

---
Desenvolvido com ❤️ usando MediaPipe e PyFirmata
