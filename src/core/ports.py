"""Heurísticas para reconhecer portas seriais pelo texto de descrição do sistema."""

_ARDUINO_HINTS = ("arduino", "ch340", "ch341", "usb-serial", "usb serial", "cp210", "ftdi", "wch")
_EEG_HINTS = ("bluetooth", "brainlink", "mindwave", "thinkgear")


def is_arduino_port_description(desc):
    d = (desc or "").lower()
    return any(h in d for h in _ARDUINO_HINTS)


def is_eeg_port_description(desc):
    d = (desc or "").lower()
    return any(h in d for h in _EEG_HINTS)
