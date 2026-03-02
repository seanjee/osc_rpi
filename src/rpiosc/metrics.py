from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
    cpu_percent: float
    mem_mb: float
    gpu_percent: float | None


class IMetricsProvider:
    def get(self) -> Metrics:
        raise NotImplementedError


class ProcMetricsProvider(IMetricsProvider):
    def __init__(self) -> None:
        self._prev_idle: int | None = None
        self._prev_total: int | None = None

    def get(self) -> Metrics:
        cpu = self._cpu_percent()
        mem = self._mem_mb()
        return Metrics(cpu_percent=cpu, mem_mb=mem, gpu_percent=None)

    def _cpu_percent(self) -> float:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            line = f.readline()
        parts = line.split()
        if len(parts) < 5 or parts[0] != "cpu":
            return 0.0
        nums = list(map(int, parts[1:]))
        idle = nums[3]
        total = sum(nums)

        if self._prev_idle is None:
            self._prev_idle = idle
            self._prev_total = total
            return 0.0

        idle_diff = idle - self._prev_idle
        total_diff = total - (self._prev_total or total)
        self._prev_idle = idle
        self._prev_total = total
        if total_diff <= 0:
            return 0.0
        return 100.0 * (1.0 - idle_diff / total_diff)

    def _mem_mb(self) -> float:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = float(parts[1])
                        return kb / 1024.0
        return 0.0
