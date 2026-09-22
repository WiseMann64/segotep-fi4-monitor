import pytest

from fi4_monitor.protocol import build_fi4_payload, build_hid_report


def test_minimal_payload_for_47_watts() -> None:
    payload = build_fi4_payload(46, "C", 28, 47)

    assert len(payload) == 64
    assert payload[0:3] == b"\x00\x01\x02"
    assert payload[3] == 46
    assert payload[5] == 0
    assert payload[6] == 28
    assert payload[7] == 47
    assert payload[34] == 0
    assert sum(payload[8:34]) == 0
    assert sum(payload[35:]) == 0


@pytest.mark.parametrize(
    ("wattage", "lower", "hundreds"),
    [(47, 47, 0), (100, 0, 1), (104, 4, 1), (123, 23, 1), (999, 99, 9)],
)
def test_wattage_encoding(wattage: int, lower: int, hundreds: int) -> None:
    payload = build_fi4_payload(50, "C", 50, wattage)
    assert payload[7] == lower
    assert payload[34] == hundreds


def test_fahrenheit_unit_aliases() -> None:
    assert build_fi4_payload(100, "F", 0, 0)[5] == 1
    assert build_fi4_payload(100, "°F", 0, 0)[5] == 1
    assert build_fi4_payload(100, "celsius", 0, 0)[5] == 0


def test_hid_report_has_zero_report_id_prefix() -> None:
    payload = bytes(64)
    report = build_hid_report(payload)
    assert len(report) == 65
    assert report[0] == 0
    assert report[1:] == payload


@pytest.mark.parametrize(
    "arguments",
    [
        (256, "C", 0, 0),
        (0, "C", 101, 0),
        (0, "C", 0, 1000),
        (0, "K", 0, 0),
    ],
)
def test_invalid_payload_values_are_rejected(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        build_fi4_payload(*arguments)
