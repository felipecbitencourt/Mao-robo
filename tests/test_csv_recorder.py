import csv

from outputs.csv_recorder import CsvRecorder


def test_records_predictions(tmp_path):
    r = CsvRecorder(str(tmp_path / "gravacoes"))
    r.write({"source": "CAMERA 1"})  # ignorado: não está gravando
    path = r.start()
    r.write({"timestamp": 1.0, "source": "CAMERA 1", "gesture_id": 15, "prediction": "MÃO ABERTA",
             "confidence": 98, "opening": {"polegar": 1.0, "indicador": 0.5}})
    assert r.stop() == path
    rows = list(csv.reader(open(path, encoding="utf-8")))
    assert rows[0] == CsvRecorder.COLUMNS
    assert len(rows) == 2
    assert rows[1][:5] == ["1.000", "CAMERA 1", "15", "MÃO ABERTA", "98"]
    assert rows[1][5:7] == ["1.000", "0.500"] and rows[1][7] == ""
