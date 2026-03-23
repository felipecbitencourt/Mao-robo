# Plano de Implementação — Hub Multimodal em PyQt

## 1. Visão Geral

Este projeto consiste no desenvolvimento de um hub integrado capaz de:

* Receber dados de múltiplas fontes:

  * Câmera (OpenCV)
  * Luva de sensores (USB)
  * EEG de 2 canais (Bluetooth)
* Processar esses dados via classificadores já implementados em Python
* Exibir o estado classificado em uma interface gráfica
* Controlar uma mão robótica via Arduino (USB)

O objetivo é tornar o sistema utilizável por usuários sem ცოდ de programação.

---

## 2. Arquitetura do Sistema

### Camadas principais

1. **Aquisição de dados (inputs)**
2. **Processamento (classificação)**
3. **Saída (interface + Arduino)**

---

## 3. Estrutura de Pastas

```
hub_project/
│
├── main.py
├── ui/
│   ├── main_window.py
│   ├── components/
│   │   ├── device_panel.py
│   │   ├── output_panel.py
│   │   ├── control_panel.py
│
├── core/
│   ├── hub_controller.py
│   ├── data_manager.py
│
├── inputs/
│   ├── camera_input.py
│   ├── glove_input.py
│   ├── eeg_input.py
│
├── processing/
│   ├── classifier.py
│
├── outputs/
│   ├── screen_output.py
│   ├── arduino_output.py
│
├── utils/
│   ├── config.py
│   ├── logger.py
│
└── assets/
```

---

## 4. Interface Gráfica (GUI)

### Estrutura da janela principal

* Sidebar: seleção de dispositivos
* Área central: visualização e resultados
* Rodapé: controles principais

---

### Componentes

#### 4.1 Painel de dispositivos

* Seleção de:

  * Câmera
  * Luva USB
  * EEG Bluetooth
* Botão “Conectar”
* Indicadores de status

---

#### 4.2 Painel de saída

* Estado classificado (texto grande)
* Confiança (%)
* Log de eventos

---

#### 4.3 Painel de controle

* Botão INICIAR
* Botão PARAR
* Botão CALIBRAR

---

## 5. Gerenciamento de Concorrência

### Uso de QThread

* Cada input roda em uma thread separada
* Processamento não deve ocorrer na thread da UI

#### Exemplo:

```python
class Worker(QThread):
    prediction_signal = pyqtSignal(str)

    def run(self):
        while self.running:
            data = self.get_data()
            pred = self.model.predict(data)
            self.prediction_signal.emit(pred)
```

---

## 6. Integração de Inputs

### 6.1 Câmera

* Biblioteca: OpenCV
* Captura contínua de frames

### 6.2 Luva (USB)

* Biblioteca: pyserial
* Leitura serial contínua

### 6.3 EEG (Bluetooth)

* Biblioteca: bleak
* Comunicação BLE

---

### Padronização de dados

Todos os inputs devem retornar:

```python
{
  "timestamp": float,
  "data": any
}
```

---

## 7. Processamento e Fusão de Dados

### Estratégias

#### Opção A — Simples

* Concatenar dados
* Classificador único

#### Opção B — Avançada

* Classificadores separados
* Combinação por média ou votação

```python
final_pred = (cam_pred + eeg_pred + glove_pred) / 3
```

---

## 8. Hub Controller

Responsável por orquestrar o sistema.

```python
class HubController:
    def __init__(self):
        self.inputs = []
        self.processor = Classifier()
        self.output = ArduinoOutput()

    def start(self):
        pass

    def stop(self):
        pass
```

---

## 9. Fluxo de Execução

1. Usuário abre aplicação
2. Seleciona dispositivos
3. Clica “Conectar”
4. Sistema inicializa inputs
5. Usuário clica “Iniciar”
6. Loop:

   * Captura dados
   * Processa
   * Atualiza interface
   * Envia comando ao Arduino

---

## 10. Experiência do Usuário (UX)

### Estados do sistema

* Desconectado
* Conectando
* Rodando

### Feedback

* Visualização em tempo real
* Indicadores claros de status

### Tratamento de erros

* Dispositivo não encontrado
* Falha de conexão
* Desconexão inesperada

---

## 11. Configuração Persistente

Arquivo JSON:

```json
{
  "last_devices": ["camera", "eeg"],
  "arduino_port": "COM3"
}
```

---

## 12. Empacotamento

### Ferramenta

* PyInstaller

### Comando

```bash
pyinstaller --onefile main.py
```

---

## 13. Roadmap de Desenvolvimento

### Fase 1

* Criar interface básica
* Layout funcional

### Fase 2

* Integrar câmera
* Exibir saída

### Fase 3

* Integrar Arduino
* Enviar comandos

### Fase 4

* Adicionar EEG e luva
* Implementar threading completo

### Fase 5

* Refinar UX
* Tratamento de erros
* Sistema de configuração

---

## 14. Boas Práticas

* Separar UI e lógica
* Usar controller central
* Evitar processamento na thread principal
* Padronizar interfaces de módulos

---

## 15. Próximos Passos

* Criar esqueleto do projeto
* Adaptar scripts existentes para módulos
* Implementar primeiro input (câmera)
* Validar pipeline completo (input → classificação → output)

---
