"""DS2 layer (BMW K-line), READ-ONLY.

DS2 frame: [address][total length][data...][XOR of all previous bytes]
Link: 9600 baud, 8 data bits, even parity, 1 stop bit.

This module only sends read commands (identification, fault memory).
No write, erase or flash command is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass

ADDR_DME = 0x12

CMD_IDENT = 0x00
CMD_READ_FAULTS = 0x04

STATUS_OK = 0xA0


class DS2Error(Exception):
    pass


class NoResponse(DS2Error):
    pass


class PortError(DS2Error):
    """Unusable serial port (missing, busy, pyserial not installed)."""


def xor_checksum(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c


def build_frame(addr: int, payload: bytes) -> bytes:
    body = bytes([addr, len(payload) + 3]) + payload
    return body + bytes([xor_checksum(body)])


def parse_frame(frame: bytes) -> tuple[int, bytes]:
    """Returns (address, data) after checking length and checksum."""
    if len(frame) < 4:
        raise DS2Error(f"frame too short ({len(frame)} bytes)")
    if frame[1] != len(frame):
        raise DS2Error(f"announced length {frame[1]} != received {len(frame)}")
    if xor_checksum(frame[:-1]) != frame[-1]:
        raise DS2Error("invalid checksum")
    return frame[0], frame[2:-1]


@dataclass
class Response:
    addr: int
    status: int
    data: bytes

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


class DS2Link:
    def __init__(self, port: str, timeout: float = 1.0):
        try:
            import serial  # pyserial
        except ImportError as e:  # pragma: no cover
            raise PortError("pyserial is not installed: pip install pyserial") from e
        try:
            self._ser = serial.Serial(
                port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
            )
        except serial.SerialException as e:
            raise PortError(f"cannot open {port}: {e}") from e

    def close(self) -> None:
        self._ser.close()

    def __enter__(self) -> "DS2Link":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _read_exact(self, n: int) -> bytes:
        buf = self._ser.read(n)
        if len(buf) != n:
            raise NoResponse(f"{len(buf)}/{n} bytes received before timeout")
        return buf

    def request(self, addr: int, payload: bytes) -> Response:
        frame = build_frame(addr, payload)
        self._ser.reset_input_buffer()
        self._ser.write(frame)
        self._ser.flush()

        # Simple K-line interfaces echo back what we transmit.
        head = self._read_exact(2)
        if head == frame[:2]:
            rest = self._read_exact(len(frame) - 2)
            if rest != frame[2:]:
                raise DS2Error("corrupted echo (wiring or interface?)")
            head = self._read_exact(2)
        resp = head + self._read_exact(max(head[1] - 2, 0))
        got_addr, body = parse_frame(resp)
        if not body:
            raise DS2Error("reply without status byte")
        return Response(got_addr, body[0], body[1:])

    def ident(self, addr: int = ADDR_DME) -> Response:
        return self.request(addr, bytes([CMD_IDENT]))

    def read_faults(self, addr: int = ADDR_DME) -> Response:
        return self.request(addr, bytes([CMD_READ_FAULTS]))
