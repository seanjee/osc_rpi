from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TriggerMode(str, Enum):
    AUTO = "Auto"
    NORMAL = "Normal"
    SINGLE = "Single"


class EdgeType(str, Enum):
    RISING = "Rising"
    FALLING = "Falling"
    BOTH = "Both"


@dataclass(frozen=True)
class ChannelConfig:
    channel_id: int
    gpio_pin: int
    physical_pin: int
    enabled: bool
    gpio_chip: str
    line: int


@dataclass(frozen=True)
class SamplingConfig:
    max_frequency: int
    depth: int
    default_time_scale_us_per_div: int


@dataclass(frozen=True)
class DisplayConfig:
    refresh_rate: int
    grid_visible: bool
    trigger_record_max: int
    screenshot_path: str
    trigger_log_path: str


@dataclass(frozen=True)
class TriggerConfig:
    default_mode: TriggerMode
    default_channel: int
    default_level_v: float
    default_edge: EdgeType
    default_holdoff_s: float


@dataclass(frozen=True)
class PerformanceConfig:
    max_cpu_load: int
    max_gpu_load: int
    target_fps: int


@dataclass(frozen=True)
class OscConfig:
    channels: list[ChannelConfig]
    external_trigger: ChannelConfig | None
    sampling: SamplingConfig
    display: DisplayConfig
    trigger: TriggerConfig
    performance: PerformanceConfig
    hotkeys: dict[str, str]
