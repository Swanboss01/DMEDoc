"""Heuristic analysis of an MS4x ECU .bin dump.

IMPORTANT: this module does NOT verify Siemens checksums (algorithms not
implemented). It only detects obvious signs of an incomplete or corrupt dump:
unexpected size, erased areas (0xFF), empty file.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass, field

# Usual flash sizes (bytes). Indicative, to be confirmed on real hardware.
KNOWN_SIZES = {
    256 * 1024: "MS41 (256 KB)",
    512 * 1024: "MS42 / MS43 (512 KB)",
    1024 * 1024: "MS45 (1 MB)",
}

BLOCK = 4096


@dataclass
class BinReport:
    path: str
    size: int
    size_hint: str | None
    sha256: str
    crc32: int
    ff_ratio: float
    zero_ratio: float
    erased_blocks: int
    total_blocks: int
    part_numbers: list[str] = field(default_factory=list)
    # (i18n key, format params): translated at display time
    warnings: list[tuple[str, dict]] = field(default_factory=list)


def analyse(data: bytes, path: str = "<mémoire>") -> BinReport:
    size = len(data)
    n = max(size, 1)
    blocks = [data[i : i + BLOCK] for i in range(0, size, BLOCK)]
    erased = sum(1 for b in blocks if b.count(0xFF) == len(b))

    # Numéros à 7 chiffres (références type 1429xxx / 7500xxx) trouvés en ASCII.
    parts = sorted({m.decode() for m in re.findall(rb"(?<!\d)\d{7}(?!\d)", data)})[:10]

    rep = BinReport(
        path=path,
        size=size,
        size_hint=KNOWN_SIZES.get(size),
        sha256=hashlib.sha256(data).hexdigest(),
        crc32=zlib.crc32(data) & 0xFFFFFFFF,
        ff_ratio=data.count(0xFF) / n,
        zero_ratio=data.count(0x00) / n,
        erased_blocks=erased,
        total_blocks=len(blocks),
        part_numbers=parts,
    )

    if size == 0:
        rep.warnings.append(("w_empty", {}))
        return rep
    if rep.size_hint is None:
        rep.warnings.append(("w_size", {"size": size}))
    if rep.ff_ratio == 1.0:
        rep.warnings.append(("w_all_ff", {}))
    elif rep.erased_blocks / len(blocks) > 0.25:
        rep.warnings.append(("w_blocks", {"n": rep.erased_blocks, "total": len(blocks)}))
    if rep.zero_ratio == 1.0:
        rep.warnings.append(("w_all_zero", {}))
    return rep


def analyse_file(path: str) -> BinReport:
    with open(path, "rb") as f:
        return analyse(f.read(), path)


def diff_ranges(a: bytes, b: bytes, max_ranges: int = 200) -> list[tuple[int, int]]:
    """Plages [début, fin[ où deux dumps diffèrent (sur la longueur commune)."""
    ranges: list[tuple[int, int]] = []
    start = None
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            if start is None:
                start = i
        elif start is not None:
            ranges.append((start, i))
            start = None
            if len(ranges) >= max_ranges:
                return ranges
    if start is not None:
        ranges.append((start, min(len(a), len(b))))
    return ranges
