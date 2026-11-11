from hardware.eeg_brainlink import BrainLinkParser


def packet(payload):
    return bytes([0xAA, 0xAA, len(payload)]) + bytes(payload) + bytes([(~sum(payload)) & 0xFF])


def test_parses_attention_meditation_signal():
    got = []
    p = BrainLinkParser(got.append)
    p.parse(b"\x00\x13" + packet([0x02, 25, 0x04, 61, 0x05, 72]))
    assert got and got[-1].signal == 25
    assert got[-1].attention == 61 and got[-1].meditation == 72


def test_bad_checksum_is_ignored():
    got = []
    p = BrainLinkParser(got.append)
    pkt = bytearray(packet([0x04, 61]))
    pkt[-1] ^= 0xFF
    p.parse(bytes(pkt))
    assert got == []


def test_split_packet_and_eeg_power():
    got = []
    p = BrainLinkParser(got.append)
    bands = []
    for v in range(1, 9):
        bands += list(v.to_bytes(3, "big"))
    pkt = packet([0x83, 24] + bands)
    p.parse(pkt[:10])
    assert got == []
    p.parse(pkt[10:])
    d = got[-1]
    assert (d.delta, d.theta, d.low_alpha, d.high_gamma) == (1, 2, 3, 8)
