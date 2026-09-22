"""Confirmed minimal Segotep FI4 payload protocol."""

from __future__ import annotations

PAYLOAD_SIZE = 64
REPORT_ID_PREFIX = b"\x00"


def _unit_byte(unit: str) -> int:
    normalized = unit.strip().upper()
    if normalized in {"C", "CELSIUS", "°C", "Â°C"}:
        return 0
    if normalized in {"F", "FAHRENHEIT", "°F", "Â°F"}:
        return 1
    raise ValueError("unit must be C or F")


def build_fi4_payload(
    temperature: int,
    unit: str,
    cpu_load: int,
    wattage: int,
) -> bytes:
    """Build the confirmed zeroed 64-byte FI4 payload."""

    unit_byte = _unit_byte(unit)

    if not isinstance(temperature, int) or not 0 <= temperature <= 255:
        raise ValueError("temperature must fit in one byte")
    if not isinstance(cpu_load, int) or not 0 <= cpu_load <= 100:
        raise ValueError("cpu_load must be between 0 and 100")
    if not isinstance(wattage, int) or not 0 <= wattage <= 999:
        raise ValueError("wattage must be between 0 and 999")

    payload = bytearray(PAYLOAD_SIZE)
    payload[0:3] = b"\x00\x01\x02"
    payload[3] = temperature
    payload[5] = unit_byte
    payload[6] = cpu_load
    payload[7] = wattage % 100
    payload[34] = wattage // 100
    return bytes(payload)


def build_hid_report(payload: bytes) -> bytes:
    """Prepend the no-report-ID prefix required by hidapi for the FI4."""

    if len(payload) != PAYLOAD_SIZE:
        raise ValueError(f"payload must be exactly {PAYLOAD_SIZE} bytes")
    return REPORT_ID_PREFIX + payload
