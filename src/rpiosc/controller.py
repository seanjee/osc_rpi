from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets


from rpiosc.config_loader import load_osc_config, load_trigger_conditions
from rpiosc.gpio_driver import FakeEdgeSource, LibgpiodEdgeSource
from rpiosc.metrics import ProcMetricsProvider
from rpiosc.models import TriggerMode
from rpiosc.storage import CsvTriggerLogWriter, TriggerRecord
from rpiosc.trigger_dsl import parse_expression
from rpiosc.trigger_engine import TriggerEngine
from rpiosc.ui_controls import Viewport, timebase_down, timebase_up


@dataclass(frozen=True)
class TriggerLogLine:
    timestamp: str
    text: str


class AppState(QtCore.QObject):
    waveform_updated = QtCore.Signal(object)  # dict
    snapshot_updated = QtCore.Signal(QtGui.QImage, str)
    screenshot_saved = QtCore.Signal(str)
    metrics_updated = QtCore.Signal(float, float, object)  # cpu, mem, gpu
    triggerlog_updated = QtCore.Signal(list)
    samplerate_updated = QtCore.Signal(int)
    mode_updated = QtCore.Signal(str)
    timebase_updated = QtCore.Signal(str)
    trigger_position_updated = QtCore.Signal(str)
    trigger_marker_updated = QtCore.Signal(float, int)  # x_seconds, channel_id
    snapshot_traces_updated = QtCore.Signal(object, str)  # traces dict, ts
    trigger_condition_updated = QtCore.Signal(str)
    holdoff_updated = QtCore.Signal(str)


class Controller(QtCore.QObject):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._stop = threading.Event()

        self.viewport = Viewport(seconds_per_div=1e-3)
        self.enabled_channels: dict[int, bool] = {1: True, 2: True, 3: True, 4: True}

        self.osc_cfg = load_osc_config("config/osc_config.yaml")
        trig_cfg = load_trigger_conditions("config/trigger_conditions.yaml")
        self.trigger_condition_text = trig_cfg.active_expression

        self.expr = parse_expression(self.trigger_condition_text)

        self.trigger_position_div = 2.5
        self.trigger_marker_channel = self.osc_cfg.trigger.default_channel
        self.last_trigger_monotonic: float | None = None
        self.holdoff_s = self.osc_cfg.trigger.default_holdoff_s

        self.engine = TriggerEngine(
            expr=self.expr,
            mode=self.osc_cfg.trigger.default_mode,
            holdoff_s=self.holdoff_s,
        )

        self.metrics = ProcMetricsProvider()
        self.log_writer = CsvTriggerLogWriter(self.osc_cfg.display.trigger_log_path)

        self.screenshot_dir = QtCore.QDir(self.osc_cfg.display.screenshot_path)
        QtCore.QDir().mkpath(self.screenshot_dir.path())
        self._trim_screenshots_keep_last(1000)

        self._trigger_lines: list[TriggerLogLine] = []
        self._trigger_lines_max = self.osc_cfg.display.trigger_record_max

        self._edge_history: dict[int, list[tuple[float, int]]] = {1: [], 2: [], 3: [], 4: []}
        self._history_window_s = 5.0

        self._frozen_traces: dict[int, tuple[list[float], list[float]]] | None = None
        self._freeze_until_monotonic: float | None = None

        self._io_queue: queue.Queue[tuple[str, QtGui.QImage, str]] = queue.Queue()

        self._edge_source = self._make_edge_source()

        self._publish_control_state()

    def _trim_screenshots_keep_last(self, keep_last: int) -> None:
        keep_last = int(keep_last)
        if keep_last <= 0:
            return

        try:
            entries = []
            for info in self.screenshot_dir.entryInfoList(
                ["Trig_*.png"],
                QtCore.QDir.Filter.Files,
                QtCore.QDir.SortFlag.Time,
            ):
                entries.append(info)

            if len(entries) <= keep_last:
                return

            for info in entries[keep_last:]:
                try:
                    QtCore.QFile.remove(info.absoluteFilePath())
                except Exception:
                    continue
        except Exception:
            return

    @QtCore.Slot(str)
    def _save_trigger_screenshot(self, ts: str) -> None:
        try:
            safe_ts = ts.replace(":", "-")
            filename = f"Trig_{safe_ts}.png"
            path = self.screenshot_dir.filePath(filename)

            w = QtWidgets.QApplication.activeWindow()
            if w is None:
                widgets = [tw for tw in QtWidgets.QApplication.topLevelWidgets() if tw.isVisible()]
                if widgets:
                    w = widgets[0]

            if w is None:
                return

            screen = w.screen() or QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                return

            pm = screen.grabWindow(w.winId())
            if pm.isNull():
                pm = w.grab()
            if pm.isNull():
                return

            out = pm.toImage()
            if out.isNull():
                return

            out.save(path, "PNG")
            self._trim_screenshots_keep_last(1000)
            self.state.screenshot_saved.emit(path)
        except Exception:
            return

    def clear_trigger_records(self) -> None:
        try:
            self._trigger_lines = []
            self.state.triggerlog_updated.emit(self._trigger_lines)

            path = QtCore.QFileInfo(self.osc_cfg.display.trigger_log_path).absoluteFilePath()
            QtCore.QDir().mkpath(QtCore.QFileInfo(path).absolutePath())
            f = QtCore.QFile(path)
            if f.open(QtCore.QIODevice.OpenModeFlag.WriteOnly | QtCore.QIODevice.OpenModeFlag.Truncate):
                f.write(b"timestamp,condition,status\n")
                f.close()

            for info in self.screenshot_dir.entryInfoList(
                ["Trig_*.png"],
                QtCore.QDir.Filter.Files,
                QtCore.QDir.SortFlag.Name,
            ):
                try:
                    QtCore.QFile.remove(info.absoluteFilePath())
                except Exception:
                    continue
        except Exception:
            return

    def _make_edge_source(self):
        chip = self.osc_cfg.channels[0].gpio_chip
        lines = {ch.channel_id: ch.line for ch in self.osc_cfg.channels if ch.enabled}

        try:
            return LibgpiodEdgeSource(chip_path=chip, lines_by_channel=lines)
        except Exception:
            return FakeEdgeSource([])

    def start(self):
        self.state.samplerate_updated.emit(self.osc_cfg.sampling.max_frequency)
        self.state.mode_updated.emit(self.engine.mode.value)
        try:
            self._edge_source.start()
        except Exception:
            self._edge_source = FakeEdgeSource([])
            self._edge_source.start()

        self._t_sample = threading.Thread(target=self._sampling_loop, daemon=True)
        self._t_metrics = threading.Thread(target=self._metrics_loop, daemon=True)
        self._t_io = threading.Thread(target=self._io_loop, daemon=True)

        self._t_sample.start()
        self._t_metrics.start()
        self._t_io.start()

    def stop(self):
        self._stop.set()
        try:
            self._edge_source.stop()
        except Exception:
            pass

    def set_mode(self, mode: TriggerMode):
        self.engine.set_mode(mode)
        self.state.mode_updated.emit(mode.value)

    def reset_single(self):
        self.engine.reset_single()

    def toggle_channel(self, ch: int, enabled: bool) -> None:
        self.enabled_channels[ch] = enabled

    def x_scale_up(self) -> None:
        self.viewport.seconds_per_div = timebase_up(self.viewport.seconds_per_div)
        self._publish_control_state()

    def x_scale_down(self) -> None:
        self.viewport.seconds_per_div = timebase_down(self.viewport.seconds_per_div)
        self._publish_control_state()

    def x_position_up(self) -> None:
        pass

    def x_position_down(self) -> None:
        pass

    def trig_position_left(self) -> None:
        self.trigger_position_div = max(0.0, self.trigger_position_div - 0.5)
        self._publish_control_state()

    def trig_position_right(self) -> None:
        self.trigger_position_div = min(5.0, self.trigger_position_div + 0.5)
        self._publish_control_state()

    def set_holdoff(self, holdoff_s: float) -> None:
        self.holdoff_s = max(0.0, holdoff_s)
        self.engine.set_holdoff(self.holdoff_s)
        self._publish_control_state()

    def set_trigger_condition(self, text: str) -> None:
        text = str(text).strip()
        expr = parse_expression(text)
        self.trigger_condition_text = text
        self.expr = expr
        self.engine.set_expr(expr)
        self._publish_control_state()

    def _publish_control_state(self) -> None:
        self.state.timebase_updated.emit(_fmt_timebase(self.viewport.seconds_per_div))
        self.state.trigger_position_updated.emit(f"{self.trigger_position_div:.1f} div")
        self.state.trigger_condition_updated.emit(self.trigger_condition_text)
        self.state.holdoff_updated.emit(_fmt_holdoff(self.holdoff_s))
        window_s = self.viewport.seconds_per_div * 5.0
        x = (self.trigger_position_div / 5.0) * window_s
        self.state.trigger_marker_updated.emit(x, int(self.trigger_marker_channel))

    def _sampling_loop(self):
        refresh_period = 1.0 / max(1, self.osc_cfg.display.refresh_rate)
        last_refresh = time.monotonic()

        while not self._stop.is_set():
            events = self._edge_source.read_events(timeout_s=0.005)

            now = time.monotonic()
            base_mono = time.monotonic()
            base_ev_ns = events[0].timestamp_ns if events else None

            for ev in events:
                if not self.enabled_channels.get(ev.channel_id, True):
                    continue
                level = 1 if ev.edge.name == "RISING" else 0
                t_mono = now
                if base_ev_ns is not None:
                    t_mono = base_mono + (ev.timestamp_ns - base_ev_ns) / 1e9
                self._edge_history.setdefault(ev.channel_id, []).append((t_mono, level))

            for ch, pts in self._edge_history.items():
                cutoff = now - self._history_window_s
                while pts and pts[0][0] < cutoff:
                    pts.pop(0)

            decision = self.engine.process(events)
            if decision is not None:
                self.last_trigger_monotonic = now

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                line = TriggerLogLine(timestamp=ts, text=f"{ts}  {decision.reason}")
                self._trigger_lines.insert(0, line)
                self._trigger_lines = self._trigger_lines[: self._trigger_lines_max]
                self.state.triggerlog_updated.emit(self._trigger_lines)

                self.log_writer.append(
                    TriggerRecord(timestamp=ts, condition="active", status=decision.reason)
                )

                self._frozen_traces = self._build_traces(time.monotonic())
                self.state.snapshot_traces_updated.emit(self._frozen_traces, ts)

                QtCore.QMetaObject.invokeMethod(
                    self.state,
                    "snapshot_updated",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(QtGui.QImage, QtGui.QImage()),
                    QtCore.Q_ARG(str, ts),
                )
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "_save_trigger_screenshot",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, ts),
                )
                if self.engine.mode == TriggerMode.AUTO:
                    self._freeze_until_monotonic = time.monotonic() + 2.0
                else:
                    self._freeze_until_monotonic = None

            if (time.monotonic() - last_refresh) >= refresh_period:
                now_refresh = time.monotonic()
                if self._frozen_traces is not None:
                    if self.engine.mode == TriggerMode.AUTO and self._freeze_until_monotonic is not None:
                        if now_refresh >= self._freeze_until_monotonic:
                            self._frozen_traces = None
                            self._freeze_until_monotonic = None
                            self.last_trigger_monotonic = None
                    if self._frozen_traces is not None:
                        self.state.waveform_updated.emit(self._frozen_traces)
                        last_refresh = now_refresh
                        continue

                window_s = self.viewport.seconds_per_div * 5.0
                cutoff = now_refresh - window_s - 0.1
                for ch, pts in self._edge_history.items():
                    while pts and pts[0][0] < cutoff:
                        pts.pop(0)

                traces = self._build_traces(now_refresh)
                self.state.waveform_updated.emit(traces)

                last_refresh = now_refresh

    def _build_traces(self, now: float):
        traces: dict[int, tuple[list[float], list[float]]] = {}
        window_s = self.viewport.seconds_per_div * 5.0

        if self.engine.mode == TriggerMode.AUTO:
            t0 = now - (self.trigger_position_div / 5.0) * window_s
        else:
            if self.last_trigger_monotonic is not None:
                t0 = self.last_trigger_monotonic - (self.trigger_position_div / 5.0) * window_s
            else:
                t0 = now - window_s
        for ch, pts in self._edge_history.items():
            if not self.enabled_channels.get(ch, True):
                continue
            if not pts:
                continue
            xs: list[float] = []
            ys: list[float] = []
            for t, level in pts:
                if t < t0:
                    continue
                x = t - t0
                if x < 0.0:
                    continue
                if x > window_s:
                    continue
                xs.append(x)
                ys.append(level)
            if xs:
                traces[ch] = (xs, ys)
        return traces

    def _render_snapshot(self) -> QtGui.QImage:
        return QtGui.QImage()

    def _metrics_loop(self):
        while not self._stop.is_set():
            m = self.metrics.get()
            self.state.metrics_updated.emit(m.cpu_percent, m.mem_mb, m.gpu_percent)
            time.sleep(0.5)

    def _io_loop(self):
        while not self._stop.is_set():
            try:
                self._io_queue.get(timeout=0.2)
            except queue.Empty:
                continue


def _fmt_timebase(seconds_per_div: float) -> str:
    if seconds_per_div < 1e-3:
        return f"{seconds_per_div*1e6:.0f} us/div"
    if seconds_per_div < 1:
        return f"{seconds_per_div*1e3:.0f} ms/div"
    return f"{seconds_per_div:.0f} s/div"


def _fmt_holdoff(holdoff_s: float) -> str:
    if holdoff_s < 1e-3:
        return f"{holdoff_s*1e6:.0f} us"
    if holdoff_s < 1:
        return f"{holdoff_s*1e3:.1f} ms"
    return f"{holdoff_s:.2f} s"
