"""Command line interface: python -m dmedoc <command>"""

from __future__ import annotations

import argparse
import sys

from .i18n import LANGS, load_saved_lang, set_lang
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
    p = argparse.ArgumentParser(prog="dmedoc", description="MS42 diagnostics (read-only) - PREVIEW")
    p.add_argument("--lang", choices=sorted(LANGS), help="output language (default: saved choice, else en)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Query the ECU over DS2 (K-line) and explain problems")
    c.add_argument("--port", required=True, help="serial port, e.g. COM3")
    c.set_defaults(func=cmd_check)

    b = sub.add_parser("bin", help="Analyse a .bin dump (no ECU needed)")
    b.add_argument("file")
    b.set_defaults(func=cmd_bin)

    d = sub.add_parser("diff", help="Compare two .bin dumps")
    d.add_argument("a")
    d.add_argument("b")
    d.set_defaults(func=cmd_diff)

    g = sub.add_parser("gui", help="Open the graphical interface")
    g.set_defaults(func=cmd_gui)

    args = p.parse_args(argv)
    if args.cmd != "gui":  # the GUI asks / loads the language itself
        set_lang(args.lang or load_saved_lang() or "en")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
