from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from rpiosc.config_loader import load_osc_config
from rpiosc.controller import AppState, Controller
from rpiosc.models import TriggerMode


class OscMainWindow(QtWidgets.QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        self.setWindowTitle("RPi5 Oscilloscope (rpiosc)")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QGridLayout(central)

        # Left-top: waveform
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True)
        self.plot.setYRange(-0.1, 1.3)
        self.plot.setXRange(0.0, 0.005, padding=0.0)
        x_axis = self.plot.getAxis("bottom")
        y_axis = self.plot.getAxis("left")

        self.plot.setLabel("bottom", "time")
        self.plot.setLabel("left", "level")

        x_axis.setLabel(text="time", units="s")
        y_axis.setLabel(text="level", units="")

        x_axis.enableAutoSIPrefix(False)
        y_axis.enableAutoSIPrefix(False)

        x_axis.setStyle(autoExpandTextSpace=True)
        y_axis.setStyle(autoExpandTextSpace=True)
        self.plot.setBackground("k")
        layout.addWidget(self.plot, 0, 0)

        self.curves = {
            1: self.plot.plot(pen=pg.mkPen("y", width=2), connect="finite"),
            2: self.plot.plot(pen=pg.mkPen("g", width=2), connect="finite"),
            3: self.plot.plot(pen=pg.mkPen("m", width=2), connect="finite"),
            4: self.plot.plot(pen=pg.mkPen("b", width=2), connect="finite"),
        }

        self.ch_colors = {
            1: "#FFFF00",
            2: "#00FF00",
            3: "#800080",
            4: "#0000FF",
        }

        self.trigger_marker = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            movable=False,
            pen=pg.mkPen("#FFFF00", width=2, style=QtCore.Qt.PenStyle.DashLine),
        )
        self.plot.addItem(self.trigger_marker)

        # Left-bottom: controls
        controls = QtWidgets.QGroupBox("Controls")
        cl = QtWidgets.QVBoxLayout(controls)

        self.sample_rate_label = QtWidgets.QLabel("fs: ?")
        self.mode_label = QtWidgets.QLabel("mode: ?")
        self.timebase_label = QtWidgets.QLabel("X: ?")
        self.trig_position_label = QtWidgets.QLabel("TrigPos: ?")
        self.trigger_condition_label = QtWidgets.QLabel("TrigCond: ?")
        self.trigger_condition_label.setWordWrap(True)
        self.trigger_condition_edit = QtWidgets.QLineEdit()
        self.trigger_condition_apply = QtWidgets.QPushButton("Apply TrigCond")
        self.holdoff_label = QtWidgets.QLabel("Holdoff: ?")
        self.cpu_label = QtWidgets.QLabel("CPU: ?")
        self.mem_label = QtWidgets.QLabel("MEM: ?")

        stats_row1 = QtWidgets.QHBoxLayout()
        stats_row1.addWidget(self.sample_rate_label)
        stats_row1.addWidget(self.mode_label)
        stats_row1.addWidget(self.timebase_label)
        stats_row1.addWidget(self.trig_position_label)
        cl.addLayout(stats_row1)

        cl.addWidget(self.trigger_condition_label)
        cl.addWidget(self.trigger_condition_edit)
        cl.addWidget(self.trigger_condition_apply)

        stats_row2 = QtWidgets.QHBoxLayout()
        stats_row2.addWidget(self.holdoff_label)
        stats_row2.addWidget(self.cpu_label)
        stats_row2.addWidget(self.mem_label)
        cl.addLayout(stats_row2)

        # Channel toggles
        self.btn_ch = {
            1: QtWidgets.QPushButton("CH1"),
            2: QtWidgets.QPushButton("CH2"),
            3: QtWidgets.QPushButton("CH3"),
            4: QtWidgets.QPushButton("CH4"),
        }
        for b in self.btn_ch.values():
            b.setCheckable(True)
            b.setChecked(True)
            b.setMinimumHeight(28)
        ch_row = QtWidgets.QHBoxLayout()
        for i in range(1, 5):
            ch_row.addWidget(self.btn_ch[i])
        cl.addLayout(ch_row)

        # Trigger mode
        self.btn_auto = QtWidgets.QPushButton("Trig Auto")
        self.btn_normal = QtWidgets.QPushButton("Trig Normal")
        self.btn_single = QtWidgets.QPushButton("Trig Single")
        tm_row = QtWidgets.QHBoxLayout()
        tm_row.addWidget(self.btn_auto)
        tm_row.addWidget(self.btn_normal)
        tm_row.addWidget(self.btn_single)
        cl.addLayout(tm_row)

        # X scale / position
        self.btn_x_up = QtWidgets.QPushButton("X Scale Up")
        self.btn_x_down = QtWidgets.QPushButton("X Scale Down")
        self.btn_x_pos_up = QtWidgets.QPushButton("X Position Up")
        self.btn_x_pos_down = QtWidgets.QPushButton("X Position Down")
        x_row1 = QtWidgets.QHBoxLayout()
        x_row1.addWidget(self.btn_x_up)
        x_row1.addWidget(self.btn_x_down)
        cl.addLayout(x_row1)
        x_row2 = QtWidgets.QHBoxLayout()
        x_row2.addWidget(self.btn_x_pos_up)
        x_row2.addWidget(self.btn_x_pos_down)
        cl.addLayout(x_row2)

        # Trigger position / holdoff
        self.btn_trig_pos_left = QtWidgets.QPushButton("Trig Position Left")
        self.btn_trig_pos_right = QtWidgets.QPushButton("Trig Position Right")
        self.btn_holdoff = QtWidgets.QPushButton("Holdoff")
        t_row = QtWidgets.QHBoxLayout()
        t_row.addWidget(self.btn_trig_pos_left)
        t_row.addWidget(self.btn_trig_pos_right)
        t_row.addWidget(self.btn_holdoff)
        cl.addLayout(t_row)

        # Other
        self.btn_fullscreen = QtWidgets.QPushButton("Fullscreen")
        self.btn_help = QtWidgets.QPushButton("Help")
        self.btn_about = QtWidgets.QPushButton("About")
        o_row = QtWidgets.QHBoxLayout()
        o_row.addWidget(self.btn_fullscreen)
        o_row.addWidget(self.btn_help)
        o_row.addWidget(self.btn_about)
        cl.addLayout(o_row)

        layout.addWidget(controls, 1, 0)

        # Right-top: snapshot
        self.snapshot_plot = pg.PlotWidget()
        self.snapshot_plot.showGrid(x=True, y=True)
        self.snapshot_plot.setYRange(-0.1, 1.3)
        self.snapshot_plot.setXRange(0.0, 0.005, padding=0.0)
        self.snapshot_plot.setBackground("#202020")
        layout.addWidget(self.snapshot_plot, 0, 1)

        self.snapshot_curves = {
            1: self.snapshot_plot.plot(pen=pg.mkPen("y", width=2), connect="finite"),
            2: self.snapshot_plot.plot(pen=pg.mkPen("g", width=2), connect="finite"),
            3: self.snapshot_plot.plot(pen=pg.mkPen("m", width=2), connect="finite"),
            4: self.snapshot_plot.plot(pen=pg.mkPen("b", width=2), connect="finite"),
        }

        self.snapshot_trigger_marker = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            movable=False,
            pen=pg.mkPen("#FFFF00", width=2, style=QtCore.Qt.PenStyle.DashLine),
        )
        self.snapshot_plot.addItem(self.snapshot_trigger_marker)

        # Right-bottom: trigger log
        trg_box = QtWidgets.QGroupBox("Trigger Log")
        trg_l = QtWidgets.QVBoxLayout(trg_box)
        self.btn_clear_trigger_log = QtWidgets.QPushButton("Clear Trigger Records")
        self.trigger_log = QtWidgets.QPlainTextEdit()
        self.trigger_log.setReadOnly(True)
        trg_l.addWidget(self.btn_clear_trigger_log)
        trg_l.addWidget(self.trigger_log)
        layout.addWidget(trg_box, 1, 1)

        # wire signals
        self.state.waveform_updated.connect(self.on_waveform)
        self.state.snapshot_traces_updated.connect(self.on_snapshot_traces)
        self.state.metrics_updated.connect(self.on_metrics)
        self.state.triggerlog_updated.connect(self.on_triggerlog)
        self.state.samplerate_updated.connect(self.on_samplerate)
        self.state.mode_updated.connect(self.on_mode)
        self.state.timebase_updated.connect(self.on_timebase)
        self.state.trigger_position_updated.connect(self.on_trigger_position)
        self.state.trigger_marker_updated.connect(self.on_trigger_marker)
        self.state.trigger_condition_updated.connect(self.on_trigger_condition)
        self.state.holdoff_updated.connect(self.on_holdoff)

    @QtCore.Slot(object)
    def on_waveform(self, traces: dict):
        y_offsets = {
            1: 0.00,
            2: 0.05,
            3: 0.10,
            4: 0.15,
        }
        for ch, curve in self.curves.items():
            xs, ys = traces.get(ch, ([], []))
            if xs:
                off = y_offsets.get(ch, 0.0)
                curve.setData(xs, [y + off for y in ys])
            else:
                curve.setData([0.0, 0.0], [0.0, 0.0])

    @QtCore.Slot(object, str)
    def on_snapshot_traces(self, traces: dict, ts: str):
        y_offsets = {
            1: 0.00,
            2: 0.05,
            3: 0.10,
            4: 0.15,
        }
        for ch, curve in self.snapshot_curves.items():
            xs, ys = traces.get(ch, ([], []))
            if xs:
                off = y_offsets.get(ch, 0.0)
                curve.setData(xs, [y + off for y in ys])
            else:
                curve.setData([0.0, 0.0], [0.0, 0.0])
        self.snapshot_plot.setToolTip(ts)

    @QtCore.Slot(float, float, object)
    def on_metrics(self, cpu: float, mem: float, gpu):
        self.cpu_label.setText(f"CPU: {cpu:.1f}%")
        self.mem_label.setText(f"MEM: {mem:.1f} MB")

    @QtCore.Slot(list)
    def on_triggerlog(self, lines: list):
        self.trigger_log.setPlainText("\n".join([l.text for l in lines]))

    @QtCore.Slot(int)
    def on_samplerate(self, hz: int):
        self.sample_rate_label.setText(f"fs: {hz} Hz")

    @QtCore.Slot(str)
    def on_mode(self, mode: str):
        self.mode_label.setText(f"mode: {mode}")

    @QtCore.Slot(str)
    def on_timebase(self, s: str):
        self.timebase_label.setText(f"X: {s}")
        secs_per_div = self._parse_timebase_seconds_per_div(s)
        if secs_per_div is not None:
            span = secs_per_div * 5.0
            self.plot.setXRange(0.0, span, padding=0.0)

    def _parse_timebase_seconds_per_div(self, s: str) -> float | None:
        try:
            parts = s.strip().split()
            if len(parts) < 2:
                return None
            value = float(parts[0])
            unit = parts[1]
            if unit.startswith("us/"):
                return value * 1e-6
            if unit.startswith("ms/"):
                return value * 1e-3
            if unit.startswith("s/"):
                return value
        except Exception:
            return None
        return None

    @QtCore.Slot(str)
    def on_trigger_position(self, s: str):
        self.trig_position_label.setText(f"TrigPos: {s}")

    @QtCore.Slot(float, int)
    def on_trigger_marker(self, x_seconds: float, ch: int):
        self.trigger_marker.setPos(x_seconds)
        self.snapshot_trigger_marker.setPos(x_seconds)
        if ch in self.ch_colors:
            color = self.ch_colors[ch]
        else:
            color = "#FFFFFF"
        pen = pg.mkPen(color, width=2, style=QtCore.Qt.PenStyle.DashLine)
        self.trigger_marker.setPen(pen)
        self.snapshot_trigger_marker.setPen(pen)

    @QtCore.Slot(str)
    def on_trigger_condition(self, s: str):
        self.trigger_condition_label.setText(f"TrigCond: {s}")
        if self.trigger_condition_edit.text().strip() != s.strip():
            self.trigger_condition_edit.setText(s)

    @QtCore.Slot(str)
    def on_holdoff(self, s: str):
        self.holdoff_label.setText(f"Holdoff: {s}")


def main():
    app = QtWidgets.QApplication([])
    state = AppState()
    win = OscMainWindow(state)

    ctrl = Controller(state)
    osc_cfg = load_osc_config("config/osc_config.yaml")

    def _apply_ch_style(ch: int, checked: bool) -> None:
        b = win.btn_ch[ch]
        if checked:
            b.setStyleSheet(f"background-color: {win.ch_colors[ch]}; color: black;")
        else:
            b.setStyleSheet("")

    shortcuts: list[QtGui.QShortcut] = []

    def _set_button_label(btn: QtWidgets.QPushButton, title: str, hotkey: str | None) -> None:
        if hotkey:
            btn.setText(f"{title} ({hotkey})")
        else:
            btn.setText(title)

    def _bind_hotkey(key: str | None, handler) -> None:
        if not key:
            return
        sc = QtGui.QShortcut(QtGui.QKeySequence(key), win)
        sc.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc.activated.connect(handler)
        shortcuts.append(sc)

    _set_button_label(win.btn_ch[1], "CH1", osc_cfg.hotkeys.get("channel1"))
    _set_button_label(win.btn_ch[2], "CH2", osc_cfg.hotkeys.get("channel2"))
    _set_button_label(win.btn_ch[3], "CH3", osc_cfg.hotkeys.get("channel3"))
    _set_button_label(win.btn_ch[4], "CH4", osc_cfg.hotkeys.get("channel4"))

    _set_button_label(win.btn_auto, "Trig Auto", osc_cfg.hotkeys.get("trig_auto"))
    _set_button_label(win.btn_normal, "Trig Normal", osc_cfg.hotkeys.get("trig_normal"))
    _set_button_label(win.btn_single, "Trig Single", osc_cfg.hotkeys.get("trig_single"))

    _set_button_label(win.btn_x_up, "X Scale Up", osc_cfg.hotkeys.get("x_scale_up"))
    _set_button_label(win.btn_x_down, "X Scale Down", osc_cfg.hotkeys.get("x_scale_down"))
    win.btn_x_pos_up.hide()
    win.btn_x_pos_down.hide()

    _set_button_label(win.btn_trig_pos_left, "Trig Position Left", osc_cfg.hotkeys.get("trig_position_left"))
    _set_button_label(win.btn_trig_pos_right, "Trig Position Right", osc_cfg.hotkeys.get("trig_position_right"))

    _set_button_label(win.btn_fullscreen, "Fullscreen", osc_cfg.hotkeys.get("fullscreen"))
    _set_button_label(win.btn_help, "Help", osc_cfg.hotkeys.get("help"))
    _set_button_label(win.btn_about, "About", osc_cfg.hotkeys.get("about"))

    def _toggle_channel_from_shortcut(ch: int) -> None:
        b = win.btn_ch[ch]
        b.toggle()

    for ch in range(1, 5):
        _apply_ch_style(ch, True)
        win.btn_ch[ch].toggled.connect(lambda checked, _ch=ch: _apply_ch_style(_ch, checked))
        win.btn_ch[ch].toggled.connect(
            lambda checked, _ch=ch: ctrl.toggle_channel(_ch, checked)
        )
        _bind_hotkey(
            osc_cfg.hotkeys.get(f"channel{ch}"),
            lambda _ch=ch: _toggle_channel_from_shortcut(_ch),
        )

    win.btn_auto.clicked.connect(lambda: ctrl.set_mode(TriggerMode.AUTO))
    win.btn_normal.clicked.connect(lambda: ctrl.set_mode(TriggerMode.NORMAL))
    win.btn_single.clicked.connect(lambda: ctrl.set_mode(TriggerMode.SINGLE))

    _bind_hotkey(osc_cfg.hotkeys.get("trig_auto"), lambda: win.btn_auto.click())
    _bind_hotkey(osc_cfg.hotkeys.get("trig_normal"), lambda: win.btn_normal.click())
    _bind_hotkey(osc_cfg.hotkeys.get("trig_single"), lambda: win.btn_single.click())

    win.btn_x_up.clicked.connect(ctrl.x_scale_up)
    win.btn_x_down.clicked.connect(ctrl.x_scale_down)
    _bind_hotkey(osc_cfg.hotkeys.get("x_scale_up"), lambda: win.btn_x_up.click())
    _bind_hotkey(osc_cfg.hotkeys.get("x_scale_down"), lambda: win.btn_x_down.click())

    win.btn_trig_pos_left.clicked.connect(ctrl.trig_position_left)
    win.btn_trig_pos_right.clicked.connect(ctrl.trig_position_right)

    win.btn_clear_trigger_log.clicked.connect(ctrl.clear_trigger_records)

    def _apply_trigger_condition() -> None:
        try:
            ctrl.set_trigger_condition(win.trigger_condition_edit.text())
        except Exception:
            pass

    win.trigger_condition_apply.clicked.connect(_apply_trigger_condition)
    win.trigger_condition_edit.returnPressed.connect(_apply_trigger_condition)
    _bind_hotkey(
        osc_cfg.hotkeys.get("trig_position_left"),
        lambda: win.btn_trig_pos_left.click(),
    )
    _bind_hotkey(
        osc_cfg.hotkeys.get("trig_position_right"),
        lambda: win.btn_trig_pos_right.click(),
    )

    win.showMaximized()
    ctrl.start()

    def _cleanup():
        ctrl.stop()

    app.aboutToQuit.connect(_cleanup)
    app.exec()


if __name__ == "__main__":
    main()
