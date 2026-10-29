"""Interface en ligne de commande : python -m dmedoc <commande>"""

from __future__ import annotations

import argparse
import re
import sys

from . import binfile, diagnose
from .ds2 import DS2Error, DS2Link


def _ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def cmd_check(args: argparse.Namespace) -> int:
    ident = None
    error: Exception | None = None
    faults = None
    try:
        with DS2Link(args.port) as link:
            ident = link.ident()
            faults = link.read_faults()
    except DS2Error as e:
        error = e

    if ident is not None:
        print(f"Identification (brut) : {ident.data.hex(' ')}")
        print(f"Identification (ASCII): {_ascii(ident.data)}")
    if faults is not None:
        print(f"Mémoire défauts (brut): {faults.data.hex(' ')}")
        print("(le décodage des codes défaut n'est pas encore implémenté)")
    print(diagnose.format_findings(diagnose.diagnose_link(error, ident)))
    return 1 if error else 0


def cmd_bin(args: argparse.Namespace) -> int:
    rep = binfile.analyse_file(args.file)
    print(f"Fichier      : {rep.path}")
    print(f"Taille       : {rep.size} octets ({rep.size_hint or 'taille inconnue'})")
    print(f"SHA-256      : {rep.sha256}")
    print(f"CRC32        : {rep.crc32:08X}")
    print(f"0xFF / 0x00  : {rep.ff_ratio:.1%} / {rep.zero_ratio:.1%}")
    print(f"Blocs vides  : {rep.erased_blocks}/{rep.total_blocks}")
    if rep.part_numbers:
        print(f"Nombres à 7 chiffres (références possibles) : {', '.join(rep.part_numbers)}")
    print(diagnose.format_findings(diagnose.diagnose_bin(rep)))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    a = open(args.a, "rb").read()
    b = open(args.b, "rb").read()
    if len(a) != len(b):
        print(f"[ATTENTION] Tailles différentes : {len(a)} vs {len(b)}")
    ranges = binfile.diff_ranges(a, b)
    if not ranges:
        print("Aucune différence sur la longueur commune.")
        return 0
    total = sum(e - s for s, e in ranges)
    print(f"{len(ranges)} plage(s) différente(s), {total} octets (max 200 plages listées) :")
    for s, e in ranges:
        print(f"  0x{s:06X} - 0x{e - 1:06X}  ({e - s} octets)")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dmedoc", description="Diagnostic MS42 (lecture seule) — PREVIEW")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Interroge le calculateur en DS2 (K-line) et explique les problèmes")
    c.add_argument("--port", required=True, help="Port série, ex. COM3")
    c.set_defaults(func=cmd_check)

    b = sub.add_parser("bin", help="Analyse un dump .bin (sans calculateur)")
    b.add_argument("file")
    b.set_defaults(func=cmd_bin)

    d = sub.add_parser("diff", help="Compare deux dumps .bin")
    d.add_argument("a")
    d.add_argument("b")
    d.set_defaults(func=cmd_diff)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
