from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Viewport:
    x_offset_s: float = 0.0
    seconds_per_div: float = 1e-3
    volts_per_div: float = 1.0
    y_offset_v: float = 0.0


_TIMEBASES_S_PER_DIV: tuple[float, ...] = (
    10e-6,
    20e-6,
    50e-6,
    100e-6,
    200e-6,
    500e-6,
    1e-3,
    2e-3,
    5e-3,
    10e-3,
    20e-3,
    50e-3,
    100e-3,
    200e-3,
    500e-3,
    1.0,
    2.0,
    5.0,
    10.0,
)

_VDIVS: tuple[float, ...] = (0.1, 0.2, 0.5, 1.0, 2.0, 5.0)


def timebase_up(current_s_per_div: float) -> float:
    idx = _closest_index(_TIMEBASES_S_PER_DIV, current_s_per_div)
    return _TIMEBASES_S_PER_DIV[max(0, idx - 1)]


def timebase_down(current_s_per_div: float) -> float:
    idx = _closest_index(_TIMEBASES_S_PER_DIV, current_s_per_div)
    return _TIMEBASES_S_PER_DIV[min(len(_TIMEBASES_S_PER_DIV) - 1, idx + 1)]


def vdiv_up(current_v_per_div: float) -> float:
    idx = _closest_index(_VDIVS, current_v_per_div)
    return _VDIVS[max(0, idx - 1)]


def vdiv_down(current_v_per_div: float) -> float:
    idx = _closest_index(_VDIVS, current_v_per_div)
    return _VDIVS[min(len(_VDIVS) - 1, idx + 1)]


def _closest_index(values: tuple[float, ...], v: float) -> int:
    return min(range(len(values)), key=lambda i: (abs(values[i] - v), i))
