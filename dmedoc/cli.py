"""Interface en ligne de commande : python -m dmedoc <commande>"""

from __future__ import annotations

import argparse
import sys

from .report import report_bin, report_check, report_diff


def cmd_check(args: argparse.Namespace) -> int:
    text, ok = report_check(args.port)
    print(text)
    return 0 if ok else 1


def cmd_bin(args: argparse.Namespace) -> int:
    print(report_bin(args.file))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    text, same = report_diff(args.a, args.b)
    print(text)
    return 0 if same else 1


def cmd_gui(args: argparse.Namespace) -> int:
    from .gui import main as gui_main

    gui_main()
    return 0


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

    g = sub.add_parser("gui", help="Ouvre l'interface graphique")
    g.set_defaults(func=cmd_gui)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
