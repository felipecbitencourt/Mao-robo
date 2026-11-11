import pytest

from processing.finger_scale import (
    FINGERS, glove_opening, legacy_from_opening, opening_from_legacy,
)


def test_legacy_round_trip():
    opening = {"polegar": 0.25, "indicador": 0.0, "medio": 0.5, "anelar": 1.0, "minimo": 0.75}
    back = opening_from_legacy(legacy_from_opening(opening))
    for k, v in opening.items():
        assert back[k] == pytest.approx(v)


def test_legacy_ranges_and_clamp():
    o = opening_from_legacy({"polegar": 50, "indicador": 180, "medio": 10, "anelar": 400, "minimo": 120})
    assert o == {"polegar": 0.0, "indicador": 1.0, "medio": 0.0, "anelar": 1.0, "minimo": 0.5}


def _glove(flex_by_finger, abduction=0.9):
    """18 sensores 5DT com a flexão dada em cada par de sensores do dedo."""
    s = [abduction] * 18
    pairs = {"polegar": (0, 1), "indicador": (3, 4), "medio": (6, 7), "anelar": (9, 10), "minimo": (12, 13)}
    for name, f in flex_by_finger.items():
        for j in pairs[name]:
            s[j] = f
    return s


def test_glove_uses_each_finger_sensors_not_first_five():
    # Só o mínimo dobrado; sensores de afastamento (2, 5, 8, 11) altos não podem fechar nada
    sensors = _glove({"polegar": 0.0, "indicador": 0.0, "medio": 0.0, "anelar": 0.0, "minimo": 1.0})
    o = glove_opening(sensors)
    assert o["minimo"] == pytest.approx(0.0)
    for name in ("polegar", "indicador", "medio", "anelar"):
        assert o[name] == pytest.approx(1.0)


def test_glove_weights_scale_flexion():
    sensors = _glove({k: 0.5 for k in FINGERS})
    o = glove_opening(sensors, weights=[2.0, 1.0, 1.0, 1.0, 0.0])
    assert o["polegar"] == pytest.approx(0.0)
    assert o["indicador"] == pytest.approx(0.5)
    assert o["minimo"] == pytest.approx(1.0)


def test_glove_thresholds_closed_when_above():
    thresholds = [0.5] * 18
    fist = glove_opening(_glove({k: 0.9 for k in FINGERS}), thresholds=thresholds)
    open_hand = glove_opening(_glove({k: 0.1 for k in FINGERS}), thresholds=thresholds)
    assert all(v == 0.0 for v in fist.values())
    assert all(v == 1.0 for v in open_hand.values())
