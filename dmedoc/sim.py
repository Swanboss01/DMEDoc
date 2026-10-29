"""Virtual car/ECU logic for the 3D simulator (no 3D dependency, unit-testable).

This is a VIRTUAL test bench: the faults are toggled by buttons and the
explanations come from the same kind of rules the real diagnosis uses. It does
not reproduce the exact behaviour of a real MS42 (not validated on hardware).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .binfile import BinReport
from .diagnose import Finding
from .ds2 import DS2Error, DS2Link, PortError
from .i18n import t


@dataclass
class SimState:
    ignition: bool = False
    fault_power: bool = False  # ECU not powered (fuse/relay/ground)
    fault_flash: bool = False  # bad / incomplete flash
    fault_crank: bool = False  # no crankshaft signal
    fault_ews: bool = False  # immobilizer (EWS) not validated
    # CRITICAL faults: could physically damage the ECU -> the simulation must halt.
    fault_overvolt: bool = False  # supply above ~16 V
    fault_reverse: bool = False  # reversed polarity on the supply
    fault_short: bool = False  # short circuit on an output (injector, coil...)

    FAULTS = ("power", "flash", "crank", "ews")
    CRITICAL = ("overvolt", "reverse", "short")

    def faults(self) -> list[str]:
        return [n for n in self.FAULTS if getattr(self, "fault_" + n)]

    def critical(self) -> list[str]:
        return [n for n in self.CRITICAL if getattr(self, "fault_" + n)]

    def can_run(self) -> bool:
        return self.ignition and not self.faults() and not self.critical()


def diagnose_sim(state: SimState) -> list[Finding]:
    """Why the engine does (not) start, most fundamental cause first."""
    crit = state.critical()
    if crit:  # protection first: nothing else matters while the ECU is at risk
        return [Finding("error", t("sf_" + n)) for n in crit] + [Finding("error", t("sf_critical_stop"))]
    if not state.ignition:
        return [Finding("info", t("sf_ign_off"))]
    if state.fault_power:
        # An unpowered ECU hides every other fault: it cannot answer anything.
        return [Finding("error", t("sf_power"))]
    out = [Finding("error", t("sf_" + name)) for name in state.faults()]
    return out or [Finding("info", t("sf_ok"))]


def flash_fault_from_bin(rep: BinReport | None) -> bool:
    """The virtual ECU's flash is bad when the loaded .bin shows obvious problems."""
    return bool(rep and rep.warnings)


def bin_summary(rep: BinReport | None) -> str:
    """Short text describing the ECU file the simulation was configured from."""
    if rep is None:
        return t("sim_bin_none")
    lines = [
        t("sim_bin_file", name=os.path.basename(rep.path)),
        t("sim_bin_type", hint=rep.size_hint or t("r_size_unknown")),
    ]
    if rep.part_numbers:
        lines.append(t("sim_bin_parts", v=", ".join(rep.part_numbers[:4])))
    lines.append(t("sim_bin_bad") if rep.warnings else t("sim_bin_ok"))
    return "\n".join(lines)


@dataclass
class RealEcu:
    ok: bool  # did the physical ECU answer on DS2?
    text: str
    pc_side: bool = False  # failure on the PC (port/driver), says nothing about the ECU


def query_real_ecu(port: str) -> RealEcu:
    """Reads the physical ECU ONCE (identification + fault memory). Read-only."""
    try:
        with DS2Link(port) as link:
            ident = link.ident()
            faults = link.read_faults()
    except PortError:
        return RealEcu(False, t("sim_ecu_port", port=port), pc_side=True)
    except DS2Error as e:
        return RealEcu(False, t("sim_ecu_none", port=port, err=e))
    ascii_ident = "".join(chr(b) if 32 <= b < 127 else "." for b in ident.data)
    text = t("sim_ecu_ok", port=port, ident=ascii_ident)
    if faults.data:
        text += "\n" + t("sim_ecu_faults", v=faults.data.hex(" "))
    return RealEcu(True, text)


@dataclass
class SimSource:
    """Where the virtual ECU's settings come from: nothing (default), a .bin, or the real ECU."""

    bin_report: BinReport | None = None
    real_ecu: RealEcu | None = None

    def flash_fault(self) -> bool:
        return flash_fault_from_bin(self.bin_report)

    def power_fault(self) -> bool:
        """A real ECU that does not answer behaves like an unpowered one."""
        return bool(self.real_ecu and not self.real_ecu.ok and not self.real_ecu.pc_side)

    def summary(self) -> str:
        if self.real_ecu:
            return self.real_ecu.text + "\n" + t("sim_ecu_note")
        return bin_summary(self.bin_report)
