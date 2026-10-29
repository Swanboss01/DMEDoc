"""Génération des rapports texte, partagée par le CLI et l'interface graphique."""

from __future__ import annotations

from . import binfile, diagnose
from .ds2 import DS2Error, DS2Link


def _ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def report_check(port: str) -> tuple[str, bool]:
    """Retourne (texte, succès)."""
    ident = None
    error: Exception | None = None
    faults = None
    try:
        with DS2Link(port) as link:
            ident = link.ident()
            faults = link.read_faults()
    except DS2Error as e:
        error = e

    lines: list[str] = []
    if ident is not None:
        lines.append(f"Identification (brut) : {ident.data.hex(' ')}")
        lines.append(f"Identification (ASCII): {_ascii(ident.data)}")
    if faults is not None:
        lines.append(f"Mémoire défauts (brut): {faults.data.hex(' ')}")
        lines.append("(le décodage des codes défaut n'est pas encore implémenté)")
    lines.append(diagnose.format_findings(diagnose.diagnose_link(error, ident)))
    return "\n".join(lines), error is None


def report_bin(path: str) -> str:
    rep = binfile.analyse_file(path)
    lines = [
        f"Fichier      : {rep.path}",
        f"Taille       : {rep.size} octets ({rep.size_hint or 'taille inconnue'})",
        f"SHA-256      : {rep.sha256}",
        f"CRC32        : {rep.crc32:08X}",
        f"0xFF / 0x00  : {rep.ff_ratio:.1%} / {rep.zero_ratio:.1%}",
        f"Blocs vides  : {rep.erased_blocks}/{rep.total_blocks}",
    ]
    if rep.part_numbers:
        lines.append(f"Nombres à 7 chiffres (références possibles) : {', '.join(rep.part_numbers)}")
    lines.append(diagnose.format_findings(diagnose.diagnose_bin(rep)))
    return "\n".join(lines)


def report_diff(path_a: str, path_b: str) -> tuple[str, bool]:
    """Retourne (texte, identiques)."""
    with open(path_a, "rb") as f:
        a = f.read()
    with open(path_b, "rb") as f:
        b = f.read()
    lines: list[str] = []
    if len(a) != len(b):
        lines.append(f"[ATTENTION] Tailles différentes : {len(a)} vs {len(b)}")
    ranges = binfile.diff_ranges(a, b)
    if not ranges:
        lines.append("Aucune différence sur la longueur commune.")
        return "\n".join(lines), True
    total = sum(e - s for s, e in ranges)
    lines.append(f"{len(ranges)} plage(s) différente(s), {total} octets (max 200 plages listées) :")
    for s, e in ranges:
        lines.append(f"  0x{s:06X} - 0x{e - 1:06X}  ({e - s} octets)")
    return "\n".join(lines), False
