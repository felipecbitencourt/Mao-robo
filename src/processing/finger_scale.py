"""
Escala única dos dedos.

Cada fonte (câmera, luva, EEG) entrega os dedos no dicionário ``fingers`` em
"unidades legadas", que a interface já sabe desenhar:

  - dedos longos (indicador..mínimo): ângulo 60 (fechado) .. 180 (aberto)
  - polegar: razão*100, 50 (fechado) .. 130 (aberto)

Para o Arduino, o hub converte isso numa única grandeza, a *abertura*
(0.0 = fechado, 1.0 = aberto), com ``opening_from_legacy``. Assim a conversão
para posição de servo existe num lugar só (``arduino_output``).
"""

FINGERS = ("polegar", "indicador", "medio", "anelar", "minimo")

THUMB_CLOSED, THUMB_OPEN = 50.0, 130.0
LONG_CLOSED, LONG_OPEN = 60.0, 180.0

# Ordem dos 18 valores enviados pela ponte da luva 5DT (TestGlove64.exe):
#  0 Thumb Near, 1 Thumb Far, 2 Thumb/Index, 3 Index Near, 4 Index Far,
#  5 Index/Middle, 6 Middle Near, 7 Middle Far, 8 Middle/Ring, 9 Ring Near,
# 10 Ring Far, 11 Ring/Little, 12 Little Near, 13 Little Far, 14 Thumb Palm,
# 15 Wrist Bend, 16 Roll, 17 Pitch
# Os sensores de flexão de cada dedo (articulação próxima e distante):
GLOVE_FINGER_SENSORS = {
    "polegar": (0, 1),
    "indicador": (3, 4),
    "medio": (6, 7),
    "anelar": (9, 10),
    "minimo": (12, 13),
}


def _clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def opening_from_legacy(fingers):
    """Converte o dicionário ``fingers`` (unidades legadas) em abertura 0..1."""
    out = {}
    for name in FINGERS:
        if name not in fingers:
            continue
        v = float(fingers[name])
        if name == "polegar":
            out[name] = _clamp01((v - THUMB_CLOSED) / (THUMB_OPEN - THUMB_CLOSED))
        else:
            out[name] = _clamp01((v - LONG_CLOSED) / (LONG_OPEN - LONG_CLOSED))
    return out


def legacy_from_opening(opening):
    """Converte abertura 0..1 de volta para as unidades legadas usadas pela UI."""
    out = {}
    for name, o in opening.items():
        o = _clamp01(o)
        if name == "polegar":
            out[name] = THUMB_CLOSED + o * (THUMB_OPEN - THUMB_CLOSED)
        else:
            out[name] = LONG_CLOSED + o * (LONG_OPEN - LONG_CLOSED)
    return out


def glove_finger_flexion(sensors, weights=None):
    """Flexão média de cada dedo (sensores 5DT normalizados: 0 = esticado, 1 = dobrado)."""
    weights = weights or [1.0] * len(FINGERS)
    out = {}
    for i, name in enumerate(FINGERS):
        idx = [j for j in GLOVE_FINGER_SENSORS[name] if j < len(sensors)]
        if not idx:
            continue
        flex = sum(sensors[j] for j in idx) / len(idx)
        w = weights[i] if i < len(weights) else 1.0
        out[name] = _clamp01(flex * w)
    return out


def glove_opening(sensors, weights=None, thresholds=None):
    """
    Abertura de cada dedo a partir dos sensores da luva.

    - Com ``thresholds`` (calibração clínica, um limiar por sensor): o dedo
      está fechado quando a média dos seus sensores passa da média dos
      limiares (mesma regra do protocolo clínico: valor >= limiar = FECHADO).
    - Sem limiares: abertura contínua = 1 - flexão*peso.
    """
    if thresholds and len(thresholds) >= 14:
        out = {}
        for name in FINGERS:
            idx = [j for j in GLOVE_FINGER_SENSORS[name] if j < len(sensors)]
            if not idx:
                continue
            val = sum(sensors[j] for j in idx) / len(idx)
            thr = sum(thresholds[j] for j in idx) / len(idx)
            out[name] = 0.0 if val >= thr else 1.0
        return out
    return {name: 1.0 - f for name, f in glove_finger_flexion(sensors, weights).items()}
