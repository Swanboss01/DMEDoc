"""Text report generation, shared by the CLI and the GUI."""

from __future__ import annotations

from . import binfile, diagnose
from .ds2 import DS2Error, DS2Link
from .i18n import t


def _ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def report_check(port: str) -> tuple[str, bool]:
    """Returns (text, success)."""
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
        lines.append(t("ident_raw", v=ident.data.hex(" ")))
        lines.append(t("ident_ascii", v=_ascii(ident.data)))
    if faults is not None:
        lines.append(t("faults_raw", v=faults.data.hex(" ")))
        lines.append(t("faults_not_decoded"))
    lines.append(diagnose.format_findings(diagnose.diagnose_link(error, ident)))
    return "\n".join(lines), error is None


def report_bin(path: str) -> str:
    rep = binfile.analyse_file(path)
    lines = [
        t("r_file", v=rep.path),
        t("r_size", size=rep.size, hint=rep.size_hint or t("r_size_unknown")),
        t("r_sha", v=rep.sha256),
        t("r_crc", v=f"{rep.crc32:08X}"),
        t("r_ratio", ff=f"{rep.ff_ratio:.1%}", zero=f"{rep.zero_ratio:.1%}"),
        t("r_blocks", n=rep.erased_blocks, total=rep.total_blocks),
    ]
    if rep.part_numbers:
        lines.append(t("r_parts", v=", ".join(rep.part_numbers)))
    lines.append(diagnose.format_findings(diagnose.diagnose_bin(rep)))
    return "\n".join(lines)


def report_diff(path_a: str, path_b: str) -> tuple[str, bool]:
    """Returns (text, identical)."""
    with open(path_a, "rb") as f:
        a = f.read()
    with open(path_b, "rb") as f:
        b = f.read()
    lines: list[str] = []
    if len(a) != len(b):
        lines.append(f"{t('lvl_warning')} {t('diff_size', a=len(a), b=len(b))}")
    ranges = binfile.diff_ranges(a, b)
    if not ranges:
        lines.append(t("diff_none"))
        return "\n".join(lines), True
    total = sum(e - s for s, e in ranges)
    lines.append(t("diff_summary", n=len(ranges), total=total))
    for s, e in ranges:
        lines.append(t("diff_line", s=s, e=e - 1, length=e - s))
    return "\n".join(lines), False
