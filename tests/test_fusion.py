import time

import pytest

pytest.importorskip("mediapipe")
from processing.hand_processor import HandProcessor


def pred(conf, value):
    return {"prediction": "x", "gesture_id": 15, "confidence": conf, "timestamp": time.time(),
            "fingers": {k: value for k in ("polegar", "indicador", "medio", "anelar", "minimo")}}


def test_single_camera_is_not_labeled_fusion():
    hp = HandProcessor()
    hp.latest_predictions = {0: pred(98, 170)}
    assert hp._fuse_predictions()["source"] == "CAMERA"


def test_two_cameras_are_fused():
    hp = HandProcessor()
    hp.latest_predictions = {0: pred(90, 180), 1: pred(90, 60)}
    out = hp._fuse_predictions()
    assert out["source"] == "FUSION"
    assert 60 < out["fingers"]["indicador"] < 180


def test_dominant_camera_wins():
    hp = HandProcessor()
    hp.latest_predictions = {0: pred(98, 180), 1: pred(10, 60)}
    assert hp._fuse_predictions()["source"] == "CAMERA"


def test_timestamps_strictly_increase_per_camera():
    hp = HandProcessor()
    ts = [hp._next_timestamp(0) for _ in range(50)]
    assert all(b > a for a, b in zip(ts, ts[1:]))
