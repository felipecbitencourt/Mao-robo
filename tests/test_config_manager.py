import json

from core.config_manager import ConfigManager


def test_migrates_existing_config_and_writes_only_local(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"arduino_port": "COM9", "glove_weights": [2, 1, 1, 1, 1]}))
    c = ConfigManager(base_dir=str(tmp_path))
    assert c.get("arduino_port") == "COM9"
    local = json.loads((tmp_path / "config.local.json").read_text())
    assert local["glove_weights"] == [2, 1, 1, 1, 1]

    c.set("arduino_port", "COM3")
    assert json.loads((tmp_path / "config.json").read_text())["arduino_port"] == "COM9"
    assert ConfigManager(base_dir=str(tmp_path)).get("arduino_port") == "COM3"
    assert not list(tmp_path.glob(".config.*.tmp"))


def test_corrupt_local_file_is_kept_aside(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"eeg_port": "COM10"}))
    (tmp_path / "config.local.json").write_text("{ quebrado")
    c = ConfigManager(base_dir=str(tmp_path))
    assert c.get("eeg_port") == "COM10"
    assert (tmp_path / "config.local.json.corrompido").exists()
