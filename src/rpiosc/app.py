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
        self.plot.setYRange(-0.2, 1.2)
        x_axis = self.plot.getAxis("bottom")
        y_axis = self.plot.getAxis("left")

        self.plot.setLabel("bottom", "time")
        self.plot.setLabel("left", "level")

        x_axis.setLabel(text="time", units="s")
        y_axis.setLabel(text="level", units="V")

        x_axis.enableAutoSIPrefix(False)
        y_axis.enableAutoSIPrefix(False)

        x_axis.setStyle(autoExpandTextSpace=True)
        y_axis.setStyle(autoExpandTextSpace=True)
        self.plot.setBackground("k")
        layout.addWidget(self.plot, 0, 0)

        self.curves = {
            1: self.plot.plot(pen=pg.mkPen("y", width=1), stepMode="right"),
            2: self.plot.plot(pen=pg.mkPen("g", width=1), stepMode="right"),
            3: self.plot.plot(pen=pg.mkPen("m", width=1), stepMode="right"),
            4: self.plot.plot(pen=pg.mkPen("b", width=1), stepMode="right"),
        }

        # Left-bottom: controls
        controls = QtWidgets.QGroupBox("Controls")
        cl = QtWidgets.QVBoxLayout(controls)
        self.sample_rate_label = QtWidgets.QLabel("fs: ?")
        self.mode_label = QtWidgets.QLabel("mode: ?")
        self.timebase_label = QtWidgets.QLabel("X: ?")
        self.vdiv_label = QtWidgets.QLabel("Y: ?")
        self.trig_level_label = QtWidgets.QLabel("Trig: ?")
        self.holdoff_label = QtWidgets.QLabel("Holdoff: ?")
        self.cpu_label = QtWidgets.QLabel("CPU: ?")
        self.mem_label = QtWidgets.QLabel("MEM: ?")
        cl.addWidget(self.sample_rate_label)
        cl.addWidget(self.mode_label)
        cl.addWidget(self.timebase_label)
        cl.addWidget(self.vdiv_label)
        cl.addWidget(self.trig_level_label)
        cl.addWidget(self.holdoff_label)
        cl.addWidget(self.cpu_label)
        cl.addWidget(self.mem_label)

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
            b.setMinimumHeight(44)
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

        # Y scale / position
        self.btn_y_up = QtWidgets.QPushButton("Y Scale Up")
        self.btn_y_down = QtWidgets.QPushButton("Y Scale Down")
        self.btn_y_pos_up = QtWidgets.QPushButton("Y Position Up")
        self.btn_y_pos_down = QtWidgets.QPushButton("Y Position Down")
        y_row1 = QtWidgets.QHBoxLayout()
        y_row1.addWidget(self.btn_y_up)
        y_row1.addWidget(self.btn_y_down)
        cl.addLayout(y_row1)
        y_row2 = QtWidgets.QHBoxLayout()
        y_row2.addWidget(self.btn_y_pos_up)
        y_row2.addWidget(self.btn_y_pos_down)
        cl.addLayout(y_row2)

        # Trigger level / holdoff
        self.btn_trig_level_up = QtWidgets.QPushButton("Trig Level Up")
        self.btn_trig_level_down = QtWidgets.QPushButton("Trig Level Down")
        self.btn_holdoff = QtWidgets.QPushButton("Holdoff")
        t_row = QtWidgets.QHBoxLayout()
        t_row.addWidget(self.btn_trig_level_up)
        t_row.addWidget(self.btn_trig_level_down)
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
        self.snapshot = QtWidgets.QLabel()
        self.snapshot.setMinimumSize(320, 240)
        self.snapshot.setAlignment(QtCore.Qt.AlignCenter)
        self.snapshot.setStyleSheet("background-color: #202020; color: white;")
        layout.addWidget(self.snapshot, 0, 1)

        # Right-bottom: trigger log
        self.trigger_log = QtWidgets.QPlainTextEdit()
        self.trigger_log.setReadOnly(True)
        layout.addWidget(self.trigger_log, 1, 1)

        # wire signals
        self.state.waveform_updated.connect(self.on_waveform)
        self.state.snapshot_updated.connect(self.on_snapshot)
        self.state.metrics_updated.connect(self.on_metrics)
        self.state.triggerlog_updated.connect(self.on_triggerlog)
        self.state.samplerate_updated.connect(self.on_samplerate)
        self.state.mode_updated.connect(self.on_mode)
        self.state.timebase_updated.connect(self.on_timebase)
        self.state.vdiv_updated.connect(self.on_vdiv)
        self.state.trigger_level_updated.connect(self.on_trigger_level)
        self.state.holdoff_updated.connect(self.on_holdoff)

    @QtCore.Slot(object)
    def on_waveform(self, traces: dict):
        for ch, curve in self.curves.items():
            xs, ys = traces.get(ch, ([], []))
            if xs:
                curve.setData(xs, ys)
            else:
                curve.clear()

    @QtCore.Slot(QtGui.QImage, str)
    def on_snapshot(self, img: QtGui.QImage, ts: str):
        pix = QtGui.QPixmap.fromImage(img)
        self.snapshot.setPixmap(pix.scaled(self.snapshot.size(), QtCore.Qt.KeepAspectRatio))
        self.snapshot.setToolTip(ts)

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

    @QtCore.Slot(str)
    def on_vdiv(self, s: str):
        self.vdiv_label.setText(f"Y: {s}")

    @QtCore.Slot(str)
    def on_trigger_level(self, s: str):
        self.trig_level_label.setText(f"Trig: {s}")

    @QtCore.Slot(str)
    def on_holdoff(self, s: str):
        self.holdoff_label.setText(f"Holdoff: {s}")


def main():
    app = QtWidgets.QApplication([])
    state = AppState()
    win = OscMainWindow(state)

    ctrl = Controller(state)
    osc_cfg = load_osc_config("config/osc_config.yaml")

    ch_colors = {
        1: "#FFFF00",
        2: "#00FF00",
        3: "#800080",
        4: "#0000FF",
    }

    def _apply_ch_style(ch: int, checked: bool) -> None:
        b = win.btn_ch[ch]
        if checked:
            b.setStyleSheet(f"background-color: {ch_colors[ch]}; color: black;")
        else:
            b.setStyleSheet("")

    def _set_button_label(btn: QtWidgets.QPushButton, title: str, hotkey: str | None) -> None:
        if hotkey:
            btn.setText(f"{title}\n({hotkey})")
        else:
            btn.setText(title)

    _set_button_label(win.btn_ch[1], "CH1", osc_cfg.hotkeys.get("channel1"))
    _set_button_label(win.btn_ch[2], "CH2", osc_cfg.hotkeys.get("channel2"))
    _set_button_label(win.btn_ch[3], "CH3", osc_cfg.hotkeys.get("channel3"))
    _set_button_label(win.btn_ch[4], "CH4", osc_cfg.hotkeys.get("channel4"))

    _set_button_label(win.btn_auto, "Trig Auto", osc_cfg.hotkeys.get("trig_auto"))
    _set_button_label(win.btn_normal, "Trig Normal", osc_cfg.hotkeys.get("trig_normal"))
    _set_button_label(win.btn_single, "Trig Single", osc_cfg.hotkeys.get("trig_single"))

    _set_button_label(win.btn_x_up, "X Scale Up", osc_cfg.hotkeys.get("x_scale_up"))
    _set_button_label(win.btn_x_down, "X Scale Down", osc_cfg.hotkeys.get("x_scale_down"))
    _set_button_label(win.btn_x_pos_up, "X Position Up", osc_cfg.hotkeys.get("x_position_up"))
    _set_button_label(win.btn_x_pos_down, "X Position Down", osc_cfg.hotkeys.get("x_position_down"))

    _set_button_label(win.btn_y_up, "Y Scale Up", osc_cfg.hotkeys.get("y_scale_up"))
    _set_button_label(win.btn_y_down, "Y Scale Down", osc_cfg.hotkeys.get("y_scale_down"))
    _set_button_label(win.btn_y_pos_up, "Y Position Up", osc_cfg.hotkeys.get("y_position_up"))
    _set_button_label(win.btn_y_pos_down, "Y Position Down", osc_cfg.hotkeys.get("y_position_down"))

    _set_button_label(win.btn_trig_level_up, "Trig Level Up", osc_cfg.hotkeys.get("trig_level_up"))
    _set_button_label(win.btn_trig_level_down, "Trig Level Down", osc_cfg.hotkeys.get("trig_level_down"))

    _set_button_label(win.btn_fullscreen, "Fullscreen", osc_cfg.hotkeys.get("fullscreen"))
    _set_button_label(win.btn_help, "Help", osc_cfg.hotkeys.get("help"))
    _set_button_label(win.btn_about, "About", osc_cfg.hotkeys.get("about"))

    for ch in range(1, 5):
        _apply_ch_style(ch, True)
        win.btn_ch[ch].toggled.connect(lambda checked, _ch=ch: _apply_ch_style(_ch, checked))
        win.btn_ch[ch].toggled.connect(
            lambda checked, _ch=ch: ctrl.toggle_channel(_ch, checked)
        )

    win.btn_auto.clicked.connect(lambda: ctrl.set_mode(TriggerMode.AUTO))
    win.btn_normal.clicked.connect(lambda: ctrl.set_mode(TriggerMode.NORMAL))
    win.btn_single.clicked.connect(lambda: ctrl.set_mode(TriggerMode.SINGLE))

    win.btn_x_up.clicked.connect(ctrl.x_scale_up)
    win.btn_x_down.clicked.connect(ctrl.x_scale_down)
    win.btn_x_pos_up.clicked.connect(ctrl.x_position_up)
    win.btn_x_pos_down.clicked.connect(ctrl.x_position_down)

    win.btn_y_up.clicked.connect(ctrl.y_scale_up)
    win.btn_y_down.clicked.connect(ctrl.y_scale_down)
    win.btn_y_pos_up.clicked.connect(ctrl.y_position_up)
    win.btn_y_pos_down.clicked.connect(ctrl.y_position_down)

    win.btn_trig_level_up.clicked.connect(ctrl.trig_level_up)
    win.btn_trig_level_down.clicked.connect(ctrl.trig_level_down)

    win.show()
    ctrl.start()

    def _cleanup():
        ctrl.stop()

    app.aboutToQuit.connect(_cleanup)
    app.exec()


if __name__ == "__main__":
    main()
