from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SamplePlan:
    requested_hz: int
    quantized_hz: int


_FIXED_RATES: tuple[int, ...] = (
    1_000,
    2_000,
    5_000,
    10_000,
    20_000,
    50_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
)


def plan_sample_rate(
    *,
    depth_points: int,
    seconds_per_div: float,
    divs: int = 10,
    safety_factor: float = 1.2,
    min_hz: int = 1_000,
    max_hz: int = 1_000_000,
) -> SamplePlan:
    if depth_points <= 0:
        raise ValueError("depth_points must be positive")
    if seconds_per_div <= 0:
        raise ValueError("seconds_per_div must be positive")
    if divs <= 0:
        raise ValueError("divs must be positive")
    if safety_factor <= 0:
        raise ValueError("safety_factor must be positive")

    time_span = seconds_per_div * divs
    requested = int(round(depth_points / (time_span * safety_factor)))
    requested = max(min_hz, min(max_hz, requested))

    quantized = min(_FIXED_RATES, key=lambda r: (abs(r - requested), r))
    quantized = max(min_hz, min(max_hz, quantized))

    return SamplePlan(requested_hz=requested, quantized_hz=quantized)
