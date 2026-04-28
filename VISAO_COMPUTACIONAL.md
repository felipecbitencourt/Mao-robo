# Módulo de Visão Computacional

## 1. Contextualização e propósito

Este documento apresenta, em nível técnico-científico, a concepção do módulo de visão computacional do sistema **Mão Robótica Multimodal Pro**. O objetivo central do módulo consiste em estimar, em tempo real, o estado cinemático dos dedos a partir de imagens monoculares (ou bicamerais), convertendo tais estimativas em comandos de controle para uma mão robótica servoacionada.

De forma específica, o módulo foi projetado para:

- adquirir fluxo de vídeo com baixa latência;
- inferir landmarks anatômicos da mão por meio do MediaPipe;
- produzir simultaneamente uma representação discreta (classe gestual) e uma representação contínua (telemetria por dedo) para atuação robótica.

## 2. Arquitetura funcional

O subsistema de visão é estruturado em três camadas principais: aquisição, processamento e orquestração.

### 2.1 Aquisição de imagem (`src/inputs/camera_input.py`)

A classe `CameraInput` opera em thread dedicada (`QThread`) e realiza a leitura contínua de frames via OpenCV, emitindo-os pelo sinal `frame_signal`. O componente suporta dois backends de captura em ambiente Windows:

- `dshow` (DirectShow), adotado como padrão;
- `msmf` (Media Foundation), empregado como alternativa de compatibilidade.

Há, adicionalmente, um procedimento de varredura de dispositivos com validação de qualidade mínima de frame, reduzindo o risco de seleção de fontes inválidas.

### 2.2 Processamento de landmarks e inferência (`src/processing/hand_processor.py`)

O processamento visual é implementado pela classe `HandProcessor`, também em thread dedicada, utilizando `MediaPipe Tasks` e o modelo local `models/hand_landmarker.task`. Para cada frame recebido, o pipeline executa:

1. conversão de espaço de cor (BGR para RGB);
2. inferência dos landmarks da mão;
3. extração de atributos geométricos (ângulos articulares e razão de distâncias);
4. determinação do `gesture_id`;
5. emissão de frame anotado e metadados de predição (`prediction`, `gesture_id`, `confidence`, `fingers`, `timestamp`).

### 2.3 Orquestração sistêmica (`src/core/hub_controller.py`)

O `HubController` integra aquisição, processamento, interface gráfica e módulo de saída robótica. Suas funções principais são:

- normalização semântica da origem de dados (`CAMERA 1`, `CAMERA 2`, `VISÃO DUAL (FUSÃO)`);
- arbitragem temporal de predições (priorização e debouncing);
- disseminação dos resultados para a UI (`prediction_signal`);
- encaminhamento de comandos para o atuador (`send_hand_command`) quando a saída robótica está habilitada.

## 3. Formulação do pipeline de inferência

### 3.1 Estimativa geométrica dos dedos longos

Para os dedos indicador, médio, anelar e mínimo, calcula-se uma métrica angular composta:

`avg_angle = 0.3 * MCP + 0.7 * PIP`

em que MCP e PIP correspondem, respectivamente, aos ângulos nas articulações metacarpofalângica e interfalângica proximal. A decisão binária de dedo estendido é obtida por limiarização:

- dedo considerado aberto se `avg_angle > 125`.

Essa regra contribui para a composição bit a bit do identificador gestual.

### 3.2 Estimativa do polegar

O polegar é modelado por uma razão geométrica:

`ratio = dist(p17, p4) / dist(p5, p0)`

A abertura é identificada quando `ratio > 0.6`. Em paralelo, o valor contínuo da razão é mantido para telemetria e para o controle fino de atuação.

### 3.3 Codificação gestual discreta

O `gesture_id` é formado pela combinação dos bits correspondentes aos dedos ativos. Para visualização e integração com o restante do sistema, utiliza-se normalização modular para o intervalo de 0 a 15 (`display_id = gesture_id % 16`), preservando casos especiais:

- `-1`: ausência de mão detectada;
- `0`: punho fechado;
- `15`: mão aberta.

## 4. Estratégia de visão dual e fusão

Quando o modo dual está ativo, cada câmera gera uma predição independente armazenada em `latest_predictions`. A fusão segue os seguintes critérios:

- descarte de amostras antigas (janela temporal de 200 ms);
- uso direto da fonte única, quando apenas uma câmera permanece válida;
- em condição de dupla validade:
  - aplicação de filtro de dominância por confiança (razão superior a 2.5);
  - média ponderada por confiança para cada dedo;
  - suavização por filtro de Kalman 1D por grau de liberdade;
  - recomputação do `gesture_id` a partir dos valores fundidos.

O resultado agregado é publicado com `source = FUSION` e apresentado na UI como `VISÃO DUAL (FUSÃO)`.

## 5. Integração com interface e telemetria

A integração em tempo real com a interface ocorre, principalmente, pelos sinais:

- `frame_signal(frame, source_id)`: renderização dos streams visuais;
- `prediction_signal(dict)`: atualização de rótulo gestual, confiança e barras dos dedos;
- `fps_signal(float)`: monitoramento de desempenho no cabeçalho da aplicação.

Do ponto de vista operacional, a interface permite seleção de câmeras primária/secundária, alternância entre captura simples e dual, e troca dinâmica do backend de vídeo.

## 6. Persistência de parâmetros experimentais

Os parâmetros críticos da visão computacional são persistidos em `config.json`, com destaque para:

- `camera_index`: índice da câmera principal;
- `camera2_index`: índice da câmera secundária;
- `camera_backend`: backend de captura (`dshow` ou `msmf`).

Essa persistência garante reprodutibilidade do ambiente entre execuções sucessivas.

## 7. Critérios de desempenho e robustez

A implementação adota mecanismos para operação em tempo real com estabilidade:

- desacoplamento entre aquisição e inferência por meio de threads independentes;
- fila de tamanho unitário, privilegiando o frame mais recente e reduzindo latência acumulada;
- emissão periódica de FPS para supervisão contínua;
- fallback de frame processado mesmo na presença de falhas pontuais de análise;
- tratamento de exceções no loop principal para evitar interrupções abruptas da aplicação.

## 8. Limitações metodológicas atuais

No estado atual do sistema, observam-se as seguintes limitações:

- inferência restrita a uma mão por frame (`num_hands=1`);
- limiares geométricos fixos (`125` para dedos longos e `0.6` para polegar), dependentes de calibração empírica;
- sensibilidade a variações de iluminação, oclusão parcial e perspectiva extrema.

## 9. Protocolo resumido de operação

1. Selecionar a webcam na aba de configurações.
2. Definir o backend de captura (`DirectShow` como padrão recomendado; `MSMF` como alternativa).
3. Ativar o modo `CÂMERA` no painel lateral.
4. Opcionalmente, habilitar `VISÃO DUAL` e escolher a fonte secundária.
5. Verificar, em tempo real, landmarks, classe gestual, confiança e telemetria contínua dos dedos.

## 10. Direções de evolução para pesquisa

Como continuidade para investigação em nível de doutorado, recomendam-se:

- calibração adaptativa de limiares por usuário e por contexto de captura;
- integração de classificador supervisionado sobre atributos temporais;
- modelagem probabilística de incerteza para suporte à tomada de decisão robótica;
- expansão para cenários de maior complexidade visual (oclusão severa e múltiplas mãos).

