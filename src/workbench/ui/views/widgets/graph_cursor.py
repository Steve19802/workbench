import logging
import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel
from engineering_notation import EngNumber
import pyqtgraph as pg

LOGGER = logging.getLogger(__name__)


class GraphCursor(QObject):
    cursor_changed = Signal(list)

    def __init__(self, name, plot, channel=0, color=None, width=None) -> None:
        super().__init__()
        self.name = name
        if color is None:
            color = "green"
        if width is None:
            width = 1
        self._color = color
        self._plot = plot
        self._channel = channel
        self._channels = self._get_channels_from_plot()
        self._vline = pg.InfiniteLine(
            angle=90, movable=True, pen=pg.mkPen(color, width=width)
        )
        self._hline = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen(color, width=width)
        )
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)

        # self._plot.scene().sigMouseMoved.connect(self.update_position)
        # self._sig_proxy = pg.SignalProxy(self._plot.scene().sigMouseMoved, rateLimit=60, slot=self.update_position)
        self._sig_proxy = pg.SignalProxy(
            self._vline.sigPositionChanged, rateLimit=60, slot=self.vline_pos_changed
        )
        self._x_is_log = False
        self._y_is_log = False
        self._ch_combo = None

        self.set_active(True)
        self._setup_panel()
        self.update_panel()

    def _setup_panel(self):
        self._frame = QFrame()
        self._frame.setObjectName("cursor_frame")
        self._frame.setStyleSheet(
            "#cursor_frame {" + f"border: 2px solid {self._color}" + "}"
        )

        layout = QGridLayout(self._frame)
        layout.setContentsMargins(5, 5, 5, 5)  # Good practice

        self._name_label = QLabel(f"{self.name}")

        self._empty_lbl = QLabel("No Channels")

        self._ch_combo = QComboBox()
        self._x_label = QLabel("x:")
        self._y_label = QLabel("y:")

        layout.addWidget(self._name_label, 0, 0)
        layout.addWidget(self._ch_combo, 0, 1)
        layout.addWidget(self._empty_lbl, 1, 0, 2, 2)  # Spans across the bottom
        layout.addWidget(self._x_label, 1, 0, 1, 2)
        layout.addWidget(self._y_label, 2, 0, 1, 2)

        # Connect signals
        self._ch_combo.currentIndexChanged.connect(self._channel_change)

    def get_panel(self):
        return self._frame

    def _get_channels_from_plot(self):
        count = 0
        channels = []
        for plot_item in self._plot.listDataItems():
            if isinstance(plot_item, pg.PlotDataItem) and plot_item.isVisible():
                if plot_item.name() is not None:
                    channels.append(plot_item.name())
                else:
                    channels.append(f"Ch{count}")
                count += 1
        print(channels)
        return channels

    def update_channels(self):
        self._channels = self._get_channels_from_plot()
        self._update_chcombo()
        x_is_log, y_is_log = self._plot.getViewBox().state["logMode"]
        self._x_is_log = x_is_log
        self._y_is_log = y_is_log
        self.update_panel()
        LOGGER.debug("Channels updated")

    def set_active(self, new_state):
        self._active = new_state
        self._vline.setVisible(new_state)
        self._hline.setVisible(new_state)

    def vline_pos_changed(self, e):
        line = e[0]
        x_pos = line.pos()[0]
        try:
            curve_point = self.get_value_from_xcoordinate(x_pos)
        except RuntimeError as e:
            curve_point = None

        if curve_point is None:
            return

        self._x = curve_point[0]
        self._y = curve_point[1]
        # self._vline.setPos(curve_point[0])
        self._hline.setPos(curve_point[1])
        self.update_panel_coordinates()
        self.cursor_changed.emit([(curve_point[0], curve_point[1])])

    def update_position(self, e):
        if not self._active:
            return

        pos = e[0]
        if self._plot.sceneBoundingRect().contains(pos):
            mousePoint = self._plot.getViewBox().mapSceneToView(pos)
            # print(f"update_position: {pos}, mousePoint: {mousePoint}")
            curve_point = self.get_value_from_xcoordinate(mousePoint.x())
            self._vline.setPos(curve_point[0])
            self._hline.setPos(curve_point[1])

            # self._vline.setPos(mousePoint.x())
            # self._hline.setPos(mousePoint.y())

    def get_value_from_xcoordinate(self, coord):
        plot_data = None
        i = 0
        for plot_item in self._plot.listDataItems():
            if isinstance(plot_item, pg.PlotDataItem):
                plot_data = plot_item
                if i == self._channel:
                    break
                else:
                    i += 1

        if plot_data is None:
            return None
            raise RuntimeError("PlotDataItem not found")

        ds = plot_data.getOriginalDataset()
        if ds is None or ds[0] is None or ds[1] is None:
            raise RuntimeError("No dataset found in plot")

        if self._x_is_log:
            print(ds[0])
            idx = (np.abs(ds[0] - np.pow(10, coord))).argmin()
        else:
            idx = (np.abs(ds[0] - coord)).argmin()
        # print(f"idx: {idx}, x: {ds[0][idx]}, y: {ds[1][idx]}")
        return (ds[0][idx], ds[1][idx])

    def update_panel(self):
        # This method can be called many times.

        if len(self._channels) == 0:
            # --- Show the "empty" state widgets ---
            self._empty_lbl.show()

            # --- Hide the "data" state widgets ---
            self._ch_combo.hide()
            self._x_label.hide()
            self._y_label.hide()
        else:
            # --- Hide the "empty" state widgets ---
            self._empty_lbl.hide()

            # --- Show the "data" state widgets ---
            self._ch_combo.show()
            self._x_label.show()
            self._y_label.show()

            # --- Update the content of the widgets ---
            # Block signals to prevent currentIndexChanged from firing during update
            self._ch_combo.blockSignals(True)

            self._ch_combo.clear()
            self._ch_combo.addItems(self._channels)
            self._ch_combo.setCurrentIndex(self._channel)

            self._ch_combo.blockSignals(False)  # Re-enable signals

    def create_panel_old(self):
        frame = self._frame
        frame.setObjectName("cursor_frame")

        frame.setStyleSheet(
            "#cursor_frame {" + f"border: 2px solid {self._color}" + "}"
        )
        # frame.setMaximumWidth(180)
        # frame.setMinimumWidth(180)

        layout = QGridLayout(frame)

        name_label = QLabel()
        name_label.setText(f"{self.name}")

        if len(self._channels) == 0:
            empty_lbl = QLabel("No Channels")
            layout.addWidget(name_label, 0, 0)
            layout.addWidget(empty_lbl, 1, 0, 2, 2)
            return frame

        ch_label = QLabel()
        ch_label.setText(f"{self._channels[self._channel]}")

        ch_combo = QComboBox()
        ch_combo.addItems(self._channels)
        ch_combo.setCurrentIndex(self._channel)
        ch_combo.currentIndexChanged.connect(self._channel_change)

        x_label = QLabel()
        x_label.setText(f"x:")

        y_label = QLabel()
        y_label.setText(f"y:")

        layout.addWidget(name_label, 0, 0)
        layout.addWidget(ch_combo, 0, 1)
        layout.addWidget(x_label, 1, 0, 1, 2)
        layout.addWidget(y_label, 2, 0, 1, 2)

        self._ch_combo = ch_combo
        self._x_label = x_label
        self._y_label = y_label

        return self._frame

    def _update_chcombo(self):
        if self._ch_combo is not None:
            self._ch_combo.clear()
            self._ch_combo.addItems(self._channels)
            self._ch_combo.setCurrentIndex(self._channel)

    def _channel_change(self, idx):
        self._channel = idx
        self.vline_pos_changed([self._vline])

    def update_panel_coordinates(self):
        self._x_label.setText(f"x: {EngNumber(self._x)}")
        self._y_label.setText(f"y: {EngNumber(self._y)}")
