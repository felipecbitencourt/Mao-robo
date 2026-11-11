import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication

from outputs.arduino_output import ArduinoOutput

app = QCoreApplication.instance() or QCoreApplication([])


class FakePin:
    def __init__(self, n, log):
        self.n, self.log = n, log

    def write(self, v):
        self.log.append((self.n, v))


class FakeBoard:
    def __init__(self):
        self.log = []
        self.digital = {p: FakePin(p, self.log) for p in range(14)}

    def exit(self):
        self.log.append("exit")


def make():
    a = ArduinoOutput()
    a.board = FakeBoard()
    a.active = True
    return a


def test_opening_maps_to_servo_positions():
    a = make()
    a.suavizar = True
    a.posicao_atual = {p: 0 for p in a.pins}
    for _ in range(40):  # o lerp converge para o alvo
        a.send_hand_command(30, opening={"indicador": 0.0, "minimo": 1.0})
    assert a.posicao_atual[9] == a.VALORES_FECHADOS[9]  # fechado
    assert a.posicao_atual[6] == 0  # aberto


def test_smoothing_off_by_default_goes_straight_to_target():
    a = make()
    assert a.suavizar is False
    a.send_hand_command(30, opening={"indicador": 0.0})
    assert a.posicao_atual[9] == a.VALORES_FECHADOS[9]
    assert a.board.log == [(9, a.VALORES_FECHADOS[9])]


def test_smoothing_on_moves_part_of_the_way():
    a = make()
    a.suavizar = True
    a.send_hand_command(30, opening={"indicador": 0.0})
    assert 0 < a.posicao_atual[9] < a.VALORES_FECHADOS[9]


def test_safe_stop_opens_hand_and_aborts_test():
    a = make()
    a.send_hand_command(0)  # fecha tudo
    a.run_test_sequence()
    time.sleep(0.3)
    assert a.safe_stop()
    assert not a.active
    assert not a.test_worker.isRunning()
    n = len(a.board.log)
    assert a.board.log[-5:] == [(p, 0) for p in a.pins]
    time.sleep(1.2)
    a.send_hand_command(0)
    assert len(a.board.log) == n  # nada é escrito depois da parada
