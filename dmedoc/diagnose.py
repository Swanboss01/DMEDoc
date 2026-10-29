"""Règles de diagnostic : transforme des constats bruts en explications lisibles."""

from __future__ import annotations

from dataclasses import dataclass

from .binfile import BinReport
from .ds2 import NoResponse, PortError, Response


@dataclass
class Finding:
    level: str  # "ERREUR" | "ATTENTION" | "INFO"
    message: str


def diagnose_link(error: Exception | None, ident: Response | None) -> list[Finding]:
    out: list[Finding] = []
    if isinstance(error, PortError):
        out.append(Finding("ERREUR", f"Problème côté PC, pas côté calculateur : {error}"))
        out.append(Finding("INFO", "Vérifier le numéro de port COM (Gestionnaire de périphériques) et qu'aucun autre logiciel (MS4x Flasher...) ne l'utilise."))
    elif isinstance(error, NoResponse):
        out.append(Finding("ERREUR", "Le calculateur ne répond pas en DS2. Vérifier dans l'ordre :"))
        for step in (
            "alimentation 12 V permanente et contact mis (+15) sur le calculateur ;",
            "masses du calculateur ;",
            "fil K-line sur la bonne broche, et câble/interface compatible 12 V ;",
            "bon port COM sélectionné (--port) ;",
            "fusible/relais DME : un calculateur éteint ne répond pas du tout.",
        ):
            out.append(Finding("INFO", "  - " + step))
        out.append(
            Finding(
                "INFO",
                "Un silence total ne prouve pas que le calculateur est mort : "
                "c'est le plus souvent un problème d'alimentation ou de câblage.",
            )
        )
    elif error is not None:
        out.append(Finding("ERREUR", f"Réponse reçue mais invalide : {error}"))
        out.append(Finding("INFO", "Parasites, écho non géré ou mauvaise interface : réessayer, vérifier le câble."))
    elif ident is not None:
        if ident.ok:
            out.append(Finding("INFO", "Le calculateur répond en DS2 : alimentation et K-line OK."))
        else:
            out.append(Finding("ATTENTION", f"Statut DS2 inattendu : 0x{ident.status:02X}"))
    return out


def diagnose_bin(rep: BinReport) -> list[Finding]:
    out = [Finding("ATTENTION", w) for w in rep.warnings]
    if not out:
        out.append(
            Finding(
                "INFO",
                "Aucun défaut évident dans le dump (cela ne remplace pas une vérification des checksums).",
            )
        )
    return out


def format_findings(findings: list[Finding]) -> str:
    return "\n".join(f"[{f.level}] {f.message}" for f in findings)
