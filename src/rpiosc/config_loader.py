from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from rpiosc.models import (
    ChannelConfig,
    DisplayConfig,
    EdgeType,
    OscConfig,
    PerformanceConfig,
    SamplingConfig,
    TriggerConfig,
    TriggerMode,
)


class ConfigError(ValueError):
    pass


def load_osc_config(path: str | Path) -> OscConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("osc_config.yaml must be a mapping")

    gpio_channels = data.get("gpio_channels")
    if not isinstance(gpio_channels, dict):
        raise ConfigError("gpio_channels missing or invalid")

    channels: list[ChannelConfig] = []
    external_trigger: ChannelConfig | None = None

    def _parse_channel(key: str, channel_id: int | None) -> ChannelConfig:
        ch = gpio_channels.get(key)
        if not isinstance(ch, dict):
            raise ConfigError(f"gpio_channels.{key} missing or invalid")
        return ChannelConfig(
            channel_id=channel_id or 0,
            gpio_pin=int(ch["gpio_pin"]),
            physical_pin=int(ch["physical_pin"]),
            enabled=bool(ch.get("enabled", True)),
            gpio_chip=str(ch["gpio_chip"]),
            line=int(ch["line"]),
        )

    for idx in range(1, 5):
        channels.append(_parse_channel(f"channel{idx}", idx))

    if "external_trigger" in gpio_channels:
        external_trigger = _parse_channel("external_trigger", None)

    sampling = data.get("sampling")
    display = data.get("display")
    trigger = data.get("trigger")
    performance = data.get("performance")
    hotkeys = data.get("hotkeys")

    if not isinstance(sampling, dict):
        raise ConfigError("sampling missing or invalid")
    if not isinstance(display, dict):
        raise ConfigError("display missing or invalid")
    if not isinstance(trigger, dict):
        raise ConfigError("trigger missing or invalid")
    if not isinstance(performance, dict):
        raise ConfigError("performance missing or invalid")
    if not isinstance(hotkeys, dict):
        raise ConfigError("hotkeys missing or invalid")

    osc = OscConfig(
        channels=channels,
        external_trigger=external_trigger,
        sampling=SamplingConfig(
            max_frequency=int(sampling["max_frequency"]),
            depth=int(sampling["depth"]),
            default_time_scale_us_per_div=int(sampling["default_time_scale"]),
        ),
        display=DisplayConfig(
            refresh_rate=int(display["refresh_rate"]),
            grid_visible=bool(display.get("grid_visible", True)),
            trigger_record_max=int(display.get("trigger_record_max", 100)),
            screenshot_path=str(display.get("screenshot_path", "./screenshots/")),
            trigger_log_path=str(display.get("trigger_log_path", "./logs/trigger_log.csv")),
        ),
        trigger=TriggerConfig(
            default_mode=TriggerMode(str(trigger["default_mode"])),
            default_channel=int(trigger["default_channel"]),
            default_level_v=float(trigger["default_level"]),
            default_edge=EdgeType(str(trigger["default_edge"])),
            default_holdoff_s=float(trigger["default_holdoff"]),
        ),
        performance=PerformanceConfig(
            max_cpu_load=int(performance.get("max_cpu_load", 90)),
            max_gpu_load=int(performance.get("max_gpu_load", 90)),
            target_fps=int(performance.get("target_fps", 30)),
        ),
        hotkeys={str(k): str(v) for k, v in hotkeys.items()},
    )

    _validate_osc_config(osc)
    return osc


def _validate_osc_config(cfg: OscConfig) -> None:
    # Validate unique chip+line
    seen: set[tuple[str, int]] = set()
    for ch in cfg.channels + ([cfg.external_trigger] if cfg.external_trigger else []):
        if ch is None:
            continue
        key = (ch.gpio_chip, ch.line)
        if key in seen:
            raise ConfigError(f"Duplicate gpio line mapping: {key}")
        seen.add(key)

    # Validate hotkeys unique values
    values = list(cfg.hotkeys.values())
    if len(values) != len(set(values)):
        raise ConfigError("Duplicate hotkey bindings in config")

    if cfg.sampling.max_frequency <= 0 or cfg.sampling.depth <= 0:
        raise ConfigError("Invalid sampling config")


@dataclass(frozen=True)
class TriggerConditionsConfig:
    active_name: str
    active_expression: str
    conditions: list[dict]


def load_trigger_conditions(path: str | Path) -> TriggerConditionsConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("trigger_conditions.yaml must be a mapping")

    conditions = data.get("trigger_conditions", [])
    if not isinstance(conditions, list):
        raise ConfigError("trigger_conditions missing or invalid")

    active = data.get("active_condition")
    if not isinstance(active, dict):
        raise ConfigError("active_condition missing or invalid")

    return TriggerConditionsConfig(
        active_name=str(active.get("name", "")),
        active_expression=str(active.get("expression", "")),
        conditions=conditions,
    )
