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
        self.last_trigger_ns: int | None = None
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

        self._edge_history: dict[int, list[tuple[int, int]]] = {1: [], 2: [], 3: [], 4: []}  # (timestamp_ns, level)
        self._history_window_ns = 5_000_000_000  # 5.0 seconds in nanoseconds

        self._frozen_traces: dict[int, tuple[list[float], list[float]]] | None = None
        self._freeze_until_ns: int | None = None

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
        # libgpiod edge timestamps are monotonic (boot-time). Keep our internal
        # timeline monotonic as well to avoid mixing epoch time with monotonic.
        last_refresh_ns = time.monotonic_ns()

        while not self._stop.is_set():
            events = self._edge_source.read_events(timeout_s=0.005)

            now_ns = time.monotonic_ns()

            for ev in events:
                if not self.enabled_channels.get(ev.channel_id, True):
                    continue
                level = 1 if ev.edge.name == "RISING" else 0
                self._edge_history.setdefault(ev.channel_id, []).append((ev.timestamp_ns, level))

            for ch, pts in self._edge_history.items():
                cutoff_ns = now_ns - self._history_window_ns
                while pts and pts[0][0] < cutoff_ns:
                    pts.pop(0)

            decision = self.engine.process(events)
            if decision is not None:
                self.last_trigger_ns = decision.timestamp_ns

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                line = TriggerLogLine(timestamp=ts, text=f"{ts}  {decision.reason}")
                self._trigger_lines.insert(0, line)
                self._trigger_lines = self._trigger_lines[: self._trigger_lines_max]
                self.state.triggerlog_updated.emit(self._trigger_lines)

                self.log_writer.append(
                    TriggerRecord(timestamp=ts, condition="active", status=decision.reason)
                )

                self._frozen_traces = self._build_traces(decision.timestamp_ns)
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
                    self._freeze_until_ns = decision.timestamp_ns + int(2.0 * 1e9)
                else:
                    self._freeze_until_ns = None

            now_ns = time.monotonic_ns()
            if (now_ns - last_refresh_ns) >= int(refresh_period * 1e9):
                now_refresh_ns = now_ns

                # Read current GPIO levels and add to history for channels without recent edges
                current_levels = self._edge_source.read_current_levels()
                for ch, level in current_levels.items():
                    if not self.enabled_channels.get(ch, True):
                        continue
                    pts = self._edge_history.get(ch, [])
                    # If no recent events or last event is too old, add current level
                    if not pts or (now_ns - pts[-1][0] > int(refresh_period * 1e9)):
                        # Only add if different from last level to avoid duplicates
                        if not pts or pts[-1][1] != level:
                            self._edge_history.setdefault(ch, []).append((now_ns, level))

                if self._frozen_traces is not None:
                    if self.engine.mode == TriggerMode.AUTO and self._freeze_until_ns is not None:
                        if now_refresh_ns >= self._freeze_until_ns:
                            self._frozen_traces = None
                            self._freeze_until_ns = None
                            self.last_trigger_ns = None
                    if self._frozen_traces is not None:
                        self.state.waveform_updated.emit(self._frozen_traces)
                        last_refresh_ns = now_refresh_ns
                        continue

                window_s = self.viewport.seconds_per_div * 5.0
                cutoff_ns = now_refresh_ns - int(window_s * 1e9) - 100_000_000  # window_s + 0.1s
                for ch, pts in self._edge_history.items():
                    while pts and pts[0][0] < cutoff_ns:
                        pts.pop(0)

                traces = self._build_traces(now_refresh_ns)
                self.state.waveform_updated.emit(traces)

                last_refresh_ns = now_refresh_ns

    def _build_traces(self, now_ns: int):
        traces: dict[int, tuple[list[float], list[float]]] = {}
        window_ns = int(self.viewport.seconds_per_div * 5.0 * 1e9)
        window_s = self.viewport.seconds_per_div * 5.0

        if self.engine.mode == TriggerMode.AUTO:
            t0_ns = now_ns - int((self.trigger_position_div / 5.0) * window_ns)
        else:
            if self.last_trigger_ns is not None:
                t0_ns = self.last_trigger_ns - int((self.trigger_position_div / 5.0) * window_ns)
            else:
                t0_ns = now_ns - window_ns

        for ch, pts in self._edge_history.items():
            if not self.enabled_channels.get(ch, True):
                continue
            if not pts:
                continue

            xs: list[float] = []
            ys: list[float] = []

            # Determine the level at the left edge (t0_ns).
            # Stored points represent the level AFTER the edge.
            prev_level: int | None = None
            first_in_window: tuple[int, int] | None = None
            for t_ns, level in pts:
                if t_ns < t0_ns:
                    prev_level = level
                    continue
                first_in_window = (t_ns, level)
                break

            if prev_level is None and first_in_window is not None:
                # If the first event we see is an edge inside the window, the
                # level just before that edge must be the opposite.
                prev_level = 1 - int(first_in_window[1])

            if prev_level is not None:
                xs.append(0.0)
                ys.append(int(prev_level))
                last_level = int(prev_level)
            else:
                last_level = None

            # Add step points within the window.
            for t_ns, level_after in pts:
                if t_ns < t0_ns:
                    continue
                x_s = (t_ns - t0_ns) / 1e9
                if x_s < 0.0:
                    continue
                if x_s > window_s:
                    continue
                level_after = int(level_after)

                if last_level is None:
                    # No baseline yet; start at this level.
                    xs.append(x_s)
                    ys.append(level_after)
                elif level_after != last_level:
                    # Vertical transition at this timestamp.
                    xs.append(x_s)
                    ys.append(last_level)
                    xs.append(x_s)
                    ys.append(level_after)
                else:
                    xs.append(x_s)
                    ys.append(level_after)

                last_level = level_after

            # Extend to the right edge so the trace fills the viewport.
            if xs and last_level is not None:
                xs.append(window_s)
                ys.append(int(last_level))

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
