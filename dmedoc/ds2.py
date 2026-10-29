"""Couche DS2 (K-line BMW) en LECTURE SEULE.

Trame DS2 : [adresse][longueur totale][données...][XOR de tous les octets précédents]
Liaison : 9600 bauds, 8 bits, parité paire, 1 stop.

Ce module n'envoie que des commandes de lecture (identification, mémoire défauts).
Aucune commande d'écriture, d'effacement ou de flash n'est implémentée.
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
    """Port série inutilisable (absent, occupé, pyserial manquant)."""


def xor_checksum(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c


def build_frame(addr: int, payload: bytes) -> bytes:
    body = bytes([addr, len(payload) + 3]) + payload
    return body + bytes([xor_checksum(body)])


def parse_frame(frame: bytes) -> tuple[int, bytes]:
    """Retourne (adresse, données) après vérification longueur + checksum."""
    if len(frame) < 4:
        raise DS2Error(f"trame trop courte ({len(frame)} octets)")
    if frame[1] != len(frame):
        raise DS2Error(f"longueur annoncée {frame[1]} != reçue {len(frame)}")
    if xor_checksum(frame[:-1]) != frame[-1]:
        raise DS2Error("checksum invalide")
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
            raise PortError("pyserial manquant : pip install pyserial") from e
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
            raise PortError(f"impossible d'ouvrir {port} : {e}") from e

    def close(self) -> None:
        self._ser.close()

    def __enter__(self) -> "DS2Link":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _read_exact(self, n: int) -> bytes:
        buf = self._ser.read(n)
        if len(buf) != n:
            raise NoResponse(f"{len(buf)}/{n} octets reçus avant timeout")
        return buf

    def request(self, addr: int, payload: bytes) -> Response:
        frame = build_frame(addr, payload)
        self._ser.reset_input_buffer()
        self._ser.write(frame)
        self._ser.flush()

        # Les interfaces K-line simples renvoient l'écho de ce qu'on émet.
        head = self._read_exact(2)
        if head == frame[:2]:
            rest = self._read_exact(len(frame) - 2)
            if rest != frame[2:]:
                raise DS2Error("écho corrompu (câblage ou interface ?)")
            head = self._read_exact(2)
        resp = head + self._read_exact(max(head[1] - 2, 0))
        got_addr, body = parse_frame(resp)
        if not body:
            raise DS2Error("réponse sans statut")
        return Response(got_addr, body[0], body[1:])

    def ident(self, addr: int = ADDR_DME) -> Response:
        return self.request(addr, bytes([CMD_IDENT]))

    def read_faults(self, addr: int = ADDR_DME) -> Response:
        return self.request(addr, bytes([CMD_READ_FAULTS]))
