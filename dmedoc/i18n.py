"""Minimal translations (English default, French optional) + saved language choice."""

from __future__ import annotations

import json
import os

DEFAULT_LANG = "en"
LANGS = {"en": "English", "fr": "Français"}

_lang = DEFAULT_LANG

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "lvl_error": "[ERROR]",
        "lvl_warning": "[WARNING]",
        "lvl_info": "[INFO]",
        # check report
        "ident_raw": "Identification (raw)  : {v}",
        "ident_ascii": "Identification (ASCII): {v}",
        "faults_raw": "Fault memory (raw)    : {v}",
        "faults_not_decoded": "(fault code decoding is not implemented yet)",
        # link diagnosis
        "port_error": "Problem on the PC side, not the ECU: {err}",
        "port_hint": "Check the COM port number (Device Manager) and that no other software (MS4x Flasher...) is using it.",
        "no_resp": "The ECU does not answer on DS2. Check, in this order:",
        "no_resp_1": "  - permanent 12 V supply and ignition on (+15) at the ECU;",
        "no_resp_2": "  - ECU grounds;",
        "no_resp_3": "  - K-line wire on the right pin, and a cable/interface compatible with 12 V;",
        "no_resp_4": "  - correct COM port selected;",
        "no_resp_5": "  - DME fuse/relay: an unpowered ECU does not answer at all.",
        "no_resp_note": "Total silence does not prove the ECU is dead: it is most often a power or wiring problem.",
        "invalid_resp": "A reply was received but it is invalid: {err}",
        "invalid_hint": "Noise, unhandled echo or wrong interface: retry and check the cable.",
        "link_ok": "The ECU answers on DS2: power and K-line are OK.",
        "status_unexpected": "Unexpected DS2 status: 0x{status:02X}",
        # bin report
        "r_file": "File         : {v}",
        "r_size": "Size         : {size} bytes ({hint})",
        "r_size_unknown": "unknown size",
        "r_sha": "SHA-256      : {v}",
        "r_crc": "CRC32        : {v}",
        "r_ratio": "0xFF / 0x00  : {ff} / {zero}",
        "r_blocks": "Empty blocks : {n}/{total}",
        "r_parts": "7-digit numbers (possible part numbers): {v}",
        "bin_no_issue": "No obvious problem in the dump (this does not replace a checksum verification).",
        "w_empty": "Empty file.",
        "w_size": "Unusual size ({size} bytes): incomplete read or a different ECU.",
        "w_all_ff": "Everything is 0xFF: memory fully erased.",
        "w_blocks": "{n}/{total} 4 KB blocks are empty (0xFF): interrupted flash or partial read likely.",
        "w_all_zero": "Everything is 0x00: failed read.",
        # diff
        "diff_size": "Different sizes: {a} vs {b}",
        "diff_none": "No difference over the common length.",
        "diff_summary": "{n} differing range(s), {total} bytes (max 200 ranges listed):",
        "diff_line": "  0x{s:06X} - 0x{e:06X}  ({length} bytes)",
        # GUI
        "title": "DMEDoc {ver} - PREVIEW (read-only)",
        "port_label": "K-line port:",
        "refresh": "Refresh",
        "btn_check": "Diagnose the ECU",
        "btn_bin": "Analyse a .bin...",
        "btn_diff": "Compare two .bin...",
        "btn_copy": "Copy report",
        "btn_lang": "Language",
        "welcome": (
            "Welcome. Preview version, never tested on a real ECU.\n"
            "Nothing is ever written to the ECU: read-only.\n\n"
            "1) Plug in the K-line cable, power the ECU (12 V + ignition), pick the port,\n"
            "   then click \"Diagnose the ECU\".\n"
            "2) Or analyse a .bin dump made with MS4x Flasher."
        ),
        "no_port": "Select a serial port (none detected? Click Refresh).",
        "querying": "Querying the ECU on {port}...",
        "unexpected": "Unexpected error: {err}",
        "dlg_bin": "Dump .bin",
        "dlg_first": "First .bin",
        "dlg_second": "Second .bin",
        "read_error": "Cannot read file: {err}",
        "lang_title": "DMEDoc - Language",
        "lang_prompt": "Choose your language / Choisissez votre langue",
    },
    "fr": {
        "lvl_error": "[ERREUR]",
        "lvl_warning": "[ATTENTION]",
        "lvl_info": "[INFO]",
        "ident_raw": "Identification (brut)  : {v}",
        "ident_ascii": "Identification (ASCII) : {v}",
        "faults_raw": "Mémoire défauts (brut) : {v}",
        "faults_not_decoded": "(le décodage des codes défaut n'est pas encore implémenté)",
        "port_error": "Problème côté PC, pas côté calculateur : {err}",
        "port_hint": "Vérifier le numéro de port COM (Gestionnaire de périphériques) et qu'aucun autre logiciel (MS4x Flasher...) ne l'utilise.",
        "no_resp": "Le calculateur ne répond pas en DS2. Vérifier dans l'ordre :",
        "no_resp_1": "  - alimentation 12 V permanente et contact mis (+15) sur le calculateur ;",
        "no_resp_2": "  - masses du calculateur ;",
        "no_resp_3": "  - fil K-line sur la bonne broche, et câble/interface compatible 12 V ;",
        "no_resp_4": "  - bon port COM sélectionné ;",
        "no_resp_5": "  - fusible/relais DME : un calculateur éteint ne répond pas du tout.",
        "no_resp_note": "Un silence total ne prouve pas que le calculateur est mort : c'est le plus souvent un problème d'alimentation ou de câblage.",
        "invalid_resp": "Réponse reçue mais invalide : {err}",
        "invalid_hint": "Parasites, écho non géré ou mauvaise interface : réessayer, vérifier le câble.",
        "link_ok": "Le calculateur répond en DS2 : alimentation et K-line OK.",
        "status_unexpected": "Statut DS2 inattendu : 0x{status:02X}",
        "r_file": "Fichier       : {v}",
        "r_size": "Taille        : {size} octets ({hint})",
        "r_size_unknown": "taille inconnue",
        "r_sha": "SHA-256       : {v}",
        "r_crc": "CRC32         : {v}",
        "r_ratio": "0xFF / 0x00   : {ff} / {zero}",
        "r_blocks": "Blocs vides   : {n}/{total}",
        "r_parts": "Nombres à 7 chiffres (références possibles) : {v}",
        "bin_no_issue": "Aucun défaut évident dans le dump (cela ne remplace pas une vérification des checksums).",
        "w_empty": "Fichier vide.",
        "w_size": "Taille inhabituelle ({size} octets) : lecture incomplète ou autre calculateur.",
        "w_all_ff": "Tout est à 0xFF : mémoire entièrement effacée.",
        "w_blocks": "{n}/{total} blocs de 4 Ko sont vides (0xFF) : flash interrompu ou lecture partielle probable.",
        "w_all_zero": "Tout est à 0x00 : lecture ratée.",
        "diff_size": "Tailles différentes : {a} vs {b}",
        "diff_none": "Aucune différence sur la longueur commune.",
        "diff_summary": "{n} plage(s) différente(s), {total} octets (max 200 plages listées) :",
        "diff_line": "  0x{s:06X} - 0x{e:06X}  ({length} octets)",
        "title": "DMEDoc {ver} - PREVIEW (lecture seule)",
        "port_label": "Port K-line :",
        "refresh": "Actualiser",
        "btn_check": "Diagnostiquer le calculateur",
        "btn_bin": "Analyser un .bin...",
        "btn_diff": "Comparer deux .bin...",
        "btn_copy": "Copier le rapport",
        "btn_lang": "Langue",
        "welcome": (
            "Bienvenue. Version preview, jamais testée sur un vrai calculateur.\n"
            "Rien n'est jamais écrit dans le calculateur : lecture seule.\n\n"
            "1) Branche le câble K-line, alimente le calculateur (12 V + contact), choisis le port,\n"
            "   puis « Diagnostiquer le calculateur ».\n"
            "2) Ou analyse un dump .bin fait avec MS4x Flasher."
        ),
        "no_port": "Choisis un port série (aucun détecté ? Clique sur Actualiser).",
        "querying": "Interrogation du calculateur sur {port}...",
        "unexpected": "Erreur inattendue : {err}",
        "dlg_bin": "Dump .bin",
        "dlg_first": "Premier .bin",
        "dlg_second": "Second .bin",
        "read_error": "Lecture impossible : {err}",
        "lang_title": "DMEDoc - Langue",
        "lang_prompt": "Choose your language / Choisissez votre langue",
    },
}


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in STRINGS else DEFAULT_LANG


def get_lang() -> str:
    return _lang


def t(key: str, **kw: object) -> str:
    text = STRINGS[_lang].get(key) or STRINGS[DEFAULT_LANG][key]
    return text.format(**kw) if kw else text


def _config_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "DMEDoc", "config.json")


def load_saved_lang() -> str | None:
    """Saved language, or None on first launch (or if the config is unreadable)."""
    try:
        with open(_config_path(), encoding="utf-8") as f:
            lang = json.load(f).get("lang")
        return lang if lang in STRINGS else None
    except (OSError, ValueError, AttributeError):
        return None


def save_lang(lang: str) -> None:
    try:
        path = _config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
    except OSError:
        pass  # the choice just won't persist
