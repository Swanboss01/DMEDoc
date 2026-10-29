"""Virtual car/ECU logic for the 3D simulator (no 3D dependency, unit-testable).

This is a VIRTUAL test bench: the faults are toggled by buttons and the
explanations come from the same kind of rules the real diagnosis uses. It does
not reproduce the exact behaviour of a real MS42 (not validated on hardware).
"""

from __future__ import annotations

from dataclasses import dataclass

from .diagnose import Finding
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
