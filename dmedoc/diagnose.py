"""Diagnosis rules: turn raw findings into readable explanations."""

from __future__ import annotations

from dataclasses import dataclass

from .binfile import BinReport
from .ds2 import NoResponse, PortError, Response
from .i18n import t


@dataclass
class Finding:
    level: str  # "error" | "warning" | "info"
    message: str


def diagnose_link(error: Exception | None, ident: Response | None) -> list[Finding]:
    out: list[Finding] = []
    if isinstance(error, PortError):
        out.append(Finding("error", t("port_error", err=error)))
        out.append(Finding("info", t("port_hint")))
    elif isinstance(error, NoResponse):
        out.append(Finding("error", t("no_resp")))
        for i in range(1, 6):
            out.append(Finding("info", t(f"no_resp_{i}")))
        out.append(Finding("info", t("no_resp_note")))
    elif error is not None:
        out.append(Finding("error", t("invalid_resp", err=error)))
        out.append(Finding("info", t("invalid_hint")))
    elif ident is not None:
        if ident.ok:
            out.append(Finding("info", t("link_ok")))
        else:
            out.append(Finding("warning", t("status_unexpected", status=ident.status)))
    return out


def diagnose_bin(rep: BinReport) -> list[Finding]:
    out = [Finding("warning", t(key, **params)) for key, params in rep.warnings]
    if not out:
        out.append(Finding("info", t("bin_no_issue")))
    return out


def format_findings(findings: list[Finding]) -> str:
    return "\n".join(f"{t('lvl_' + f.level)} {f.message}" for f in findings)
