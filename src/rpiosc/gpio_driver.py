from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

try:
    import gpiod  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    gpiod = None


class EdgeKind(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"


@dataclass(frozen=True)
class EdgeEvent:
    channel_id: int
    timestamp_ns: int
    edge: EdgeKind


class IGpioEdgeSource(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def read_events(self, timeout_s: float) -> list[EdgeEvent]: ...


class FakeEdgeSource:
    def __init__(self, events: list[EdgeEvent]):
        self._events = list(events)
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def read_events(self, timeout_s: float) -> list[EdgeEvent]:
        if not self._started:
            return []
        if not self._events:
            time.sleep(timeout_s)
            return []
        # Return all remaining deterministically
        ev, self._events = self._events, []
        return ev


class LibgpiodEdgeSource(IGpioEdgeSource):
    def __init__(self, *, chip_path: str, lines_by_channel: dict[int, int]):
        if gpiod is None:
            raise RuntimeError("python gpiod module not installed in this environment")
        self._chip_path = chip_path
        self._lines_by_channel = dict(lines_by_channel)
        self._chip: "gpiod.Chip | None" = None
        self._request: "gpiod.LineRequest | None" = None
        self._offset_by_channel: dict[int, int] = {}

    def start(self) -> None:
        # gpiod v2 API: request_lines() returns a LineRequest used for wait/read.
        self._chip = gpiod.Chip(self._chip_path)
        config: dict[int, gpiod.LineSettings] = {}
        for offset in self._lines_by_channel.values():
            s = gpiod.LineSettings(edge_detection=gpiod.line.Edge.BOTH)
            config[offset] = s
        self._request = self._chip.request_lines(config, consumer="rpiosc", event_buffer_size=4096)
        self._offset_by_channel = {ch: offset for ch, offset in self._lines_by_channel.items()}

    def stop(self) -> None:
        if self._request is not None:
            try:
                self._request.release()
            except Exception:
                pass
        self._request = None
        self._offset_by_channel.clear()
        if self._chip is not None:
            try:
                self._chip.close()
            except Exception:
                pass
        self._chip = None

    def read_events(self, timeout_s: float) -> list[EdgeEvent]:
        if self._request is None:
            return []

        from datetime import timedelta

        out: list[EdgeEvent] = []
        if not self._request.wait_edge_events(timedelta(seconds=timeout_s)):
            return out
        events = self._request.read_edge_events()

        # Build reverse mapping offset->channel
        ch_by_offset = {off: ch for ch, off in self._offset_by_channel.items()}

        for ev in events:
            ch = ch_by_offset.get(ev.line_offset)
            if ch is None:
                continue
            if ev.event_type == ev.Type.RISING_EDGE:
                edge = EdgeKind.RISING
            else:
                edge = EdgeKind.FALLING
            out.append(EdgeEvent(channel_id=ch, timestamp_ns=int(ev.timestamp_ns), edge=edge))

        return out
