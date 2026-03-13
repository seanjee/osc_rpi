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
from rpiosc.trigger_dsl import (
    And,
    ChannelEdge,
    ChannelLevel,
    Expr,
    Not,
    Or,
    ParseError,
    WithinAfter,
    WithinBefore,
    parse_expression,
)
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

        self.osc_cfg = load_osc_config("config/osc_config.yaml")
        try:
            default_us_per_div = int(self.osc_cfg.sampling.default_time_scale_us_per_div)
            default_s_per_div = max(1e-9, default_us_per_div * 1e-6)
        except Exception:
            default_s_per_div = 2e-3

        self.viewport = Viewport(seconds_per_div=default_s_per_div)
        self.enabled_channels: dict[int, bool] = {1: True, 2: True, 3: True, 4: True}

        trig_cfg = load_trigger_conditions("config/trigger_conditions.yaml")
        self.trigger_condition_text = trig_cfg.active_expression

        # Parse trigger expression from config. If invalid, fall back to a safe default
        # and surface the error in the Trigger Log so the UI still starts.
        try:
            self.expr = parse_expression(self.trigger_condition_text)
        except ParseError as e:
            bad = self.trigger_condition_text
            self.trigger_condition_text = "CH1 Rising"
            self.expr = parse_expression(self.trigger_condition_text)
            self._append_trigger_log(
                f"TrigCond ParseError at pos {e.position}: {e}. Using default '{self.trigger_condition_text}'. Bad expr: '{bad}'"
            )

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

        # Per-channel history points in monotonic nanoseconds.
        # Points come from two sources:
        # - edge events (timestamp is the kernel event timestamp; level is the level AFTER the edge)
        # - sampled levels (timestamp is when we sampled; level is the current level)
        # We keep the source flag so rendering can draw vertical transitions only for edge points.
        self._edge_history: dict[int, list[tuple[int, int, bool]]] = {1: [], 2: [], 3: [], 4: []}  # (timestamp_ns, level, is_edge)
        self._history_window_ns = 5_000_000_000  # 5.0 seconds in nanoseconds

        self._frozen_traces: dict[int, tuple[list[float], list[float]]] | None = None
        self._freeze_until_ns: int | None = None

        # Pending trigger capture: delay snapshot/freeze until we have post-trigger samples.
        # Values are in time.monotonic_ns() domain for the deadline.
        self._pending_trigger: tuple[int, int, str] | None = None  # (trigger_ts_ns, deadline_mono_ns, ts_str)

        self._io_queue: queue.Queue[tuple[str, QtGui.QImage, str]] = queue.Queue()

        self._edge_source = self._make_edge_source()

        self._publish_control_state()

    def _append_trigger_log(self, message: str) -> None:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            text = f"{ts}  {message}"
            self._trigger_lines.insert(0, TriggerLogLine(timestamp=ts, text=text))
            self._trigger_lines = self._trigger_lines[: self._trigger_lines_max]
            self.state.triggerlog_updated.emit(self._trigger_lines)
        except Exception:
            return

    def log_message(self, message: str) -> None:
        self._append_trigger_log(message)

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

            # Ensure the UI has had a chance to repaint with the latest snapshot.
            try:
                w.repaint()
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass

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
        except Exception as e:
            # Make failures visible: this otherwise degrades silently and looks
            # like "no waveform / no trigger".
            try:
                self._append_trigger_log(
                    f"GPIO init failed ({type(e).__name__}: {e}). Using FakeEdgeSource"
                )
            except Exception:
                pass
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
        try:
            expr = parse_expression(text)
        except ParseError as e:
            # Keep current expression unchanged; surface the error to the user.
            self._append_trigger_log(
                f"TrigCond ParseError at pos {e.position}: {e}. Expr: '{text}'"
            )
            raise

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
                self._edge_history.setdefault(ev.channel_id, []).append((int(ev.timestamp_ns), int(level), True))

            for ch, pts in self._edge_history.items():
                cutoff_ns = now_ns - self._history_window_ns
                while pts and pts[0][0] < cutoff_ns:
                    pts.pop(0)

            # If we are currently capturing post-trigger data for a pending snapshot, suppress new triggers.
            decision = None
            if self._pending_trigger is None:
                decision = self.engine.process(events)

            if decision is not None:
                self.last_trigger_ns = decision.timestamp_ns

                # Prefer marker channel inferred from the trigger condition expression.
                ch = _preferred_marker_channel(self.expr)
                if ch is not None:
                    self.trigger_marker_channel = int(ch)
                elif decision.channel_id is not None:
                    self.trigger_marker_channel = int(decision.channel_id)

                window_s = self.viewport.seconds_per_div * 5.0
                x = (self.trigger_position_div / 5.0) * window_s
                self.state.trigger_marker_updated.emit(x, int(self.trigger_marker_channel))

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                detail = (decision.detail or "").strip()
                status = (decision.reason + (f" {detail}" if detail else "")).strip()

                # Record trigger immediately (log + CSV). Snapshot/freeze happens after post-trigger window is captured.
                self._append_trigger_log(status)
                self.log_writer.append(
                    TriggerRecord(
                        timestamp=ts,
                        condition=self.trigger_condition_text,
                        status=status,
                    )
                )

                # Delay snapshot until enough post-trigger time has elapsed so the window contains both
                # pre-trigger and post-trigger samples.
                window_ns = int(window_s * 1e9)
                pre_ns = int((self.trigger_position_div / 5.0) * window_ns)
                post_ns = max(0, window_ns - pre_ns)
                deadline_mono = time.monotonic_ns() + int(post_ns)
                self._pending_trigger = (int(decision.timestamp_ns), int(deadline_mono), ts)

            now_ns = time.monotonic_ns()
            if (now_ns - last_refresh_ns) >= int(refresh_period * 1e9):
                now_refresh_ns = now_ns

                # Finalize pending snapshot once we've captured enough post-trigger data.
                if self._pending_trigger is not None:
                    trig_ts_ns, deadline_mono_ns, trig_ts_str = self._pending_trigger
                    if now_refresh_ns >= deadline_mono_ns:
                        snapshot_traces = self._build_traces(trig_ts_ns, anchor="trigger")
                        self.state.snapshot_traces_updated.emit(snapshot_traces, trig_ts_str)

                        QtCore.QMetaObject.invokeMethod(
                            self.state,
                            "snapshot_updated",
                            QtCore.Qt.QueuedConnection,
                            QtCore.Q_ARG(QtGui.QImage, QtGui.QImage()),
                            QtCore.Q_ARG(str, trig_ts_str),
                        )
                        QtCore.QMetaObject.invokeMethod(
                            self,
                            "_save_trigger_screenshot",
                            QtCore.Qt.QueuedConnection,
                            QtCore.Q_ARG(str, trig_ts_str),
                        )

                        # Apply live-view freezing policy once snapshot is ready.
                        if self.engine.mode == TriggerMode.AUTO:
                            self._frozen_traces = snapshot_traces
                            self._freeze_until_ns = time.monotonic_ns() + int(2.0 * 1e9)
                        elif self.engine.mode == TriggerMode.SINGLE:
                            self._frozen_traces = snapshot_traces
                            self._freeze_until_ns = None
                        elif self.engine.mode == TriggerMode.NORMAL:
                            self._frozen_traces = snapshot_traces
                            self._freeze_until_ns = None
                        else:
                            self._frozen_traces = None
                            self._freeze_until_ns = None

                        self._pending_trigger = None

                # Read current GPIO levels and add to history for channels without recent edges
                current_levels = self._edge_source.read_current_levels()
                for ch, level in current_levels.items():
                    if not self.enabled_channels.get(ch, True):
                        continue
                    pts = self._edge_history.get(ch, [])
                    # If no recent events or last event is too old, add current level
                    if not pts or (now_ns - pts[-1][0] > int(refresh_period * 1e9)):
                        # Only add if different from last level to avoid duplicates
                        if not pts or pts[-1][1] != int(level):
                            self._edge_history.setdefault(ch, []).append((now_ns, int(level), False))

                if self._frozen_traces is not None:
                    # If mode changed to something that shouldn't freeze, unfreeze immediately.
                    if self.engine.mode not in (TriggerMode.AUTO, TriggerMode.SINGLE):
                        self._frozen_traces = None
                        self._freeze_until_ns = None
                        self.last_trigger_ns = None

                    if (
                        self._frozen_traces is not None
                        and self.engine.mode == TriggerMode.AUTO
                        and self._freeze_until_ns is not None
                        and now_refresh_ns >= self._freeze_until_ns
                    ):
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

                # Live view: place the newest sample at the right edge of the viewport.
                traces = self._build_traces(now_refresh_ns, anchor="right")
                self.state.waveform_updated.emit(traces)

                last_refresh_ns = now_refresh_ns

    def _build_traces(self, now_ns: int, *, anchor: str = "right"):
        traces: dict[int, tuple[list[float], list[float]]] = {}
        window_ns = int(self.viewport.seconds_per_div * 5.0 * 1e9)
        window_s = self.viewport.seconds_per_div * 5.0

        if anchor == "trigger":
            # Align the given timestamp (typically the trigger) to the trigger marker position.
            t0_ns = now_ns - int((self.trigger_position_div / 5.0) * window_ns)
        else:
            # Default rolling behavior: newest point at right edge.
            t0_ns = now_ns - window_ns

        for ch, pts in self._edge_history.items():
            if not self.enabled_channels.get(ch, True):
                continue
            if not pts:
                continue

            xs: list[float] = []
            ys: list[float] = []

            # Determine the level at the left edge (t0_ns).
            prev_level: int | None = None
            first_in_window: tuple[int, int, bool] | None = None
            for t_ns, level, is_edge in pts:
                if t_ns < t0_ns:
                    prev_level = int(level)
                    continue
                first_in_window = (t_ns, int(level), bool(is_edge))
                break

            if prev_level is None and first_in_window is not None:
                # If the first point is an edge, infer the level before it.
                # If it's a sampled level, use it as the baseline.
                if first_in_window[2]:
                    prev_level = 1 - int(first_in_window[1])
                else:
                    prev_level = int(first_in_window[1])

            if prev_level is not None:
                xs.append(0.0)
                ys.append(int(prev_level))
                last_level: int | None = int(prev_level)
            else:
                last_level = None

            # Add points within the window.
            for t_ns, level, is_edge in pts:
                if t_ns < t0_ns:
                    continue
                x_s = (t_ns - t0_ns) / 1e9
                if x_s < 0.0:
                    continue
                if x_s > window_s:
                    continue

                level = int(level)
                is_edge = bool(is_edge)

                if is_edge:
                    # Edge point: draw a vertical transition.
                    if last_level is None:
                        last_level = 1 - level
                    if level != last_level:
                        xs.append(x_s)
                        ys.append(int(last_level))
                        xs.append(x_s)
                        ys.append(int(level))
                    else:
                        xs.append(x_s)
                        ys.append(int(level))
                    last_level = level
                else:
                    # Sampled level: draw as a regular point.
                    xs.append(x_s)
                    ys.append(int(level))
                    last_level = level

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


def _preferred_marker_channel(expr: Expr) -> int | None:
    # Prefer the anchor channel for timing expressions so "... after/before CH1 ..." is marked on CH1.
    if isinstance(expr, ChannelEdge):
        return int(expr.channel)
    if isinstance(expr, ChannelLevel):
        return int(expr.channel)
    if isinstance(expr, WithinAfter):
        return _preferred_marker_channel(expr.anchor) or _preferred_marker_channel(expr.expr)
    if isinstance(expr, WithinBefore):
        return _preferred_marker_channel(expr.anchor) or _preferred_marker_channel(expr.expr)
    if isinstance(expr, Not):
        return _preferred_marker_channel(expr.expr)
    if isinstance(expr, And):
        return _preferred_marker_channel(expr.left) or _preferred_marker_channel(expr.right)
    if isinstance(expr, Or):
        return _preferred_marker_channel(expr.left) or _preferred_marker_channel(expr.right)
    return None


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
