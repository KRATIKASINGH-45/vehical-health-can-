"""CAN frame definition shared by the transmitter and receiver nodes.

Classic CAN 2.0A data frame: 11-bit identifier + up to 8 data bytes.
Payload layout (8 bytes, big-endian), identical to the STM32 firmware in /firmware:

  byte 0-1  int16   temperature        0.1 degC / LSB
  byte 2-3  uint16  vibration          1 mg / LSB   (0.001 g)
  byte 4-5  uint16  engine speed       1 rpm / LSB
  byte 6    uint8   rolling sequence counter (0-255)
  byte 7    uint8   CRC-8 (poly 0x07) over bytes 0-6   (application-level check)

Note: real CAN already has a 15-bit hardware CRC; the extra byte lets the
simulator inject and detect payload corruption end to end.
"""
from dataclasses import dataclass
import struct

NODE_NAMES = {0x101: "ENGINE", 0x102: "TRANSMISSION", 0x103: "CHASSIS"}
VALID_IDS = set(NODE_NAMES)


def crc8(data: bytes, poly: int = 0x07, init: int = 0x00) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


@dataclass(frozen=True)
class CanFrame:
    can_id: int
    data: bytes          # always 8 bytes
    timestamp: str = ""  # logging time (not part of the physical frame)

    def __post_init__(self):
        if not 0 <= self.can_id <= 0x7FF:
            raise ValueError("11-bit identifier required")
        if len(self.data) != 8:
            raise ValueError("payload must be exactly 8 bytes")


def encode(can_id: int, temp_c: float, vib_g: float, rpm: int, seq: int, timestamp: str = "") -> CanFrame:
    t = int(round(temp_c * 10))
    v = int(round(vib_g * 1000))
    r = int(rpm)
    if not -32768 <= t <= 32767 or not 0 <= v <= 65535 or not 0 <= r <= 65535:
        raise ValueError("signal out of range for payload encoding")
    body = struct.pack(">hHHB", t, v, r, seq & 0xFF)
    return CanFrame(can_id, body + bytes([crc8(body)]), timestamp)


def decode(frame: CanFrame):
    """Return (temp_c, vib_g, rpm, seq). Raises ValueError on CRC mismatch."""
    body, rx_crc = frame.data[:7], frame.data[7]
    if crc8(body) != rx_crc:
        raise ValueError("CRC mismatch")
    t, v, r, seq = struct.unpack(">hHHB", body)
    return t / 10.0, v / 1000.0, r, seq
