from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Timebase:
    seconds_per_div: float


# From PRD.md recommended sequence (10 div): 10μs/div .. 10s/div
DEFAULT_TIMEBASES: tuple[Timebase, ...] = (
    Timebase(10e-6),
    Timebase(20e-6),
    Timebase(50e-6),
    Timebase(100e-6),
    Timebase(200e-6),
    Timebase(500e-6),
    Timebase(1e-3),
    Timebase(2e-3),
    Timebase(5e-3),
    Timebase(10e-3),
    Timebase(20e-3),
    Timebase(50e-3),
    Timebase(100e-3),
    Timebase(200e-3),
    Timebase(500e-3),
    Timebase(1.0),
    Timebase(2.0),
    Timebase(5.0),
    Timebase(10.0),
)
