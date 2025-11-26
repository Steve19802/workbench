import logging
import numpy as np
import pyqtgraph as pg
import qtawesome as qta
from workbench.core.helpers.media_ring_buffer import MediaRingBuffer
from PySide6.QtCore import (
    QEvent,
    QLocale,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QDoubleValidator, QIcon, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QMenu,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QWidgetAction,
)
from PySide6.QtSvg import QSvgGenerator

from ...viewmodels import ScopeViewModel
from .graph_cursor import GraphCursor
from .legend_select import LegendSelect
from .control_panel_widget import ControlPanelWidget
from .scale_control_widget import ScaleControlWidget
from workbench.utils import PerformanceMonitorService
from .dynamic_flow_layout import DynamicFlowLayout

LOGGER = logging.getLogger(__name__)

# LOGGER.setLevel("DEBUG")


class Trigger:
    SLOPE_POSITIVE = "pos"
    SLOPE_NEGATIVE = "neg"

    def __init__(self) -> None:
        self.level = 0.5
        self.slope = Trigger.SLOPE_POSITIVE
        self.channel = 0

    def get_trigger_idx(self, data):
        if self.level > np.max(np.abs(data[:, self.channel])):
            return 0

        data_diff = np.diff(
            data[:, self.channel], axis=0, prepend=data[0, self.channel]
        )
        data_slope = (
            (data_diff < 0) if self.slope == self.SLOPE_POSITIVE else (data_diff > 0)
        )
        trigger_idx = np.argmin(
            np.abs(data[:, self.channel] - self.level + data_slope * 10)
        )
        return trigger_idx


class CustomLogAxis(pg.AxisItem):
    """
    A custom axis item to override log tick string formatting.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def logTickStrings(self, values, scale, spacing):
        """
        Re-implement this method to customize the tick labels.
        """
        # The default implementation returns strings like "10^3", "10^6", etc.
        # You can call it as a fallback if needed:
        # return super().logTickStrings(values, scale, spacing)

        # Custom implementation: Format ticks as "1k", "1M", etc.
        lin_values = 10 ** np.array(values).astype(float) * np.array(scale)
        strings = []
        for v in lin_values:
            if v == 0:
                strings.append("0")
                continue
            # Use engineering notation (k, M, G, etc.)
            s = f" {pg.functions.siFormat(v, suffix='')} "  # 'U' can be any unit
            strings.append(s)
        return strings


class MultiToolBar(QToolBar):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # We need a child widget to hold the layout
        container = QWidget(self)
        self.layout = QHBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Add the container to the toolbar
        self.addWidget(container)

        self.toolbars = []

    def add_toolbar(self, toolbar: QToolBar):
        """Adds a child toolbar to this container."""
        self.layout.addWidget(toolbar)
        self.toolbars.append(toolbar)


class GraphControllerWidget(QWidget):
    # data_changed = Signal(np.ndarray)
    filter_channel = Signal(list)
    legend_state = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        pg.setConfigOptions(antialias=True, background=None)

        self._flow_layout = DynamicFlowLayout(self)
        self._control_panel = ControlPanelWidget(self)

        self._curves = None
        self._create_graph()
        self._plot_container = QWidget()
        self._plot_layout = QVBoxLayout(self._plot_container)
        self._plot_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_layout.addWidget(self._plot)

        # self._yrange = AutoScale(self._set_yrange)
        # self._vscale_controller = ScaleController(self)
        # self._vscale_controller.mode_changed.connect(self.set_scale_mode)
        # self._vscale_controller.manual_range_changed.connect(self.set_yrange)
        # self._vscale_controller.set_initial_mode(self._yrange._mode)
        # self._y_scale_controller = ScaleController()
        # self._y_scale_controller_view = ScaleControllerView(self._y_scale_controller)

        self._flow_layout.setCentralWidget(self._plot_container)
        self._flow_layout.setSideWidget(self._control_panel)

        self._create_toolbar()

        self.filter_channel.connect(self.set_channel_filter)
        self.legend_state.connect(self.set_legend_state)

        self._update_perf = PerformanceMonitorService().new_timer("Graphic Update")

        self._trigger_enabled = False

        self._trigger_toolbar.setVisible(False)
        self._trigger = Trigger()
        self._trigger_bar = pg.InfiniteLine(
            angle=0, movable=True, pos=(0, self._trigger.level)
        )
        self._trigger_bar.hide()
        self._trigger_bar.sigPositionChanged.connect(self._trigger_level_bar_changed)
        self._plot.addItem(self._trigger_bar)
        self._update_trigger_level_txt(self._trigger.level)
        if self._trigger.slope == Trigger.SLOPE_POSITIVE:
            self._trigger_pos_slope_action.setChecked(True)
        else:
            self._trigger_neg_slope_action.setChecked(True)

        self._cursor1 = GraphCursor("Cursor 1", self._plot, color="green", width=2)
        self._cursor1.cursor_changed.connect(self._cursor_changed)

        self._cursor2 = GraphCursor("Cursor 2", self._plot, color="blue", width=2)
        self._cursor2.cursor_changed.connect(self._cursor_changed)

        # self._side_panel_layout.addWidget(self._cursor1.create_panel())
        # self._side_panel_layout.addWidget(self._cursor2.create_panel())

        # self._side_panel_layout.addStretch()

        self._control_panel.addControlWidget(self._cursor1.get_panel())
        self._control_panel.addControlWidget(self._cursor2.get_panel())
        self._control_panel.setOrientation(Qt.Orientation.Vertical)

        self._active_channels = None

    def bind_view_model(self, view_model: ScopeViewModel):
        self._view_model = view_model

        self._view_model.view_input_format_changed.connect(self.on_format_changed)
        self._view_model.view_data_received.connect(self.on_data_received)
        self._view_model.view_vertical_range_changed.connect(self.on_yrange_changed)

        self._yscale_controls = ScaleControlWidget(view_model)

        self._scale_toolbar.addWidget(self._create_yscale_toolbar())

    def changeEvent(self, event: QEvent, /) -> None:
        if event.type() == QEvent.Type.StyleChange:
            qta.reset_cache()
            self._plot.setVisible(False)
            self._plot.setVisible(True)

        return super().changeEvent(event)

    def configure_graph(self, media_info, xaxis_log=False):
        block_size = media_info.blocksize
        LOGGER.debug(f"block_size type: {type(block_size)}, value: {block_size}")
        self._active_channels = range(len(media_info.channels))

        # Remove all curves
        if self._curves:
            for curve in self._curves:
                self._plot.removeItem(curve)

        # Create new curves
        self._curves = [
            self._plot.plot(
                name=media_info.channels[ch].name,
                pen=pg.mkPen(pg.intColor(i), width=1),
                autoDownsample=True,
                skipFiniteCheck=True,
            )
            for i, ch in enumerate(self._active_channels)
        ]

        if xaxis_log:
            self._plot.setLogMode(x=True, y=False)

        self._x = np.arange(block_size) / media_info.samplerate
        self._buf = MediaRingBuffer(
            capacity=2 * block_size, dtype=media_info.dtype, allow_overwrite=False
        )
        self._blocksize = block_size
        self._trigger_src_cbox.clear()
        for i in self._active_channels:
            self._trigger_src_cbox.addItem(media_info.channels[i].name, userData=i)

        self._cursor1.update_channels()
        self._cursor2.update_channels()

        self._legend.update(linked_curves=self._curves)

        # self._main_layout.addWidget(self._cursor1.create_panel(), 1, 4)
        # self._main_layout.addWidget(self._cursor2.create_panel(), 2, 4)

        # Legend
        # legend = LegendSelect(linked_curves=self._curves)
        # qgrp_legend = QtWidgets.QGroupBox("")
        # qgrp_legend = QWidget()
        # qgrp_legend.setMaximumWidth(180)
        # qgrp_legend.setLayout(legend.grid)
        # self._main_layout.addWidget(qgrp_legend, 0, 4)
        # self._side_panel_layout.addWidget(qgrp_legend)

        # self._side_panel_layout.addWidget(self._cursor1.create_panel())
        # self._side_panel_layout.addWidget(self._cursor2.create_panel())

        # self._side_panel_layout.addStretch()

    def _create_graph(self):
        custom_log_x_axis = CustomLogAxis(orientation="bottom")
        custom_log_x_axis.setStyle(**{"textFillLimits": [(0, 0.1)]})
        self._plot = pg.PlotWidget(
            name="time-plot", axisItems={"bottom": custom_log_x_axis}, background=None
        )

        # use negative margins to avoid clipping the very bottom pixels
        # self._plot.setViewportMargins(-40, -40, -40, -40)

        # self._legend = self._plot.addLegend()
        self._plot.showGrid(True, True)

        # plot_item = self._plot.getPlotItem()
        # if plot_item is not None: plot_item.setContentsMargins(10,0,0,10)

        # self._main_layout.addWidget(self._plot, 0, 0)

        # Legend
        self._legend = LegendSelect()
        # qgrp_legend = QWidget()
        # qgrp_legend.setMaximumWidth(180)
        # qgrp_legend.setMinimumWidth(180)
        # qgrp_legend.setLayout(legend.grid)
        # self._qgrp_legend = qgrp_legend
        # self._main_layout.addWidget(qgrp_legend, 0, 4)
        # self._side_panel_layout.addWidget(qgrp_legend)
        # self._control_panel.addControlWidget(qgrp_legend)
        self._control_panel.addControlWidget(self._legend.widget)

    def _set_yrange(self, min, max):
        self._plot.setYRange(min, max)

    def _cursor_changed(self, values):
        print(f"{self.sender().name}: {values}")

    def _create_yscale_toolbar(self):
        tool_btn = QToolButton()
        tool_btn.setPopupMode(QToolButton.MenuButtonPopup)
        tool_btn.setIcon(qta.icon("mdi6.arrow-expand-vertical"))
        menu = QMenu(tool_btn)
        action = QWidgetAction(menu)
        action.setDefaultWidget(self._yscale_controls)
        menu.addAction(action)
        tool_btn.setMenu(menu)
        return tool_btn

    def _create_toolbar(self):
        self._toolbar_widget = MultiToolBar("My toolbar")
        # self._toolbar_widget = QWidget()
        # self._toolbar_layout = QHBoxLayout(self._toolbar_widget)
        # self._toolbar_layout.setContentsMargins(0, 0, 0, 0)
        # self._toolbar_layout.setSpacing(0)

        self._toolbar = QToolBar("My main toolbar")
        self._toolbar.setIconSize(QSize(16, 16))
        self._toolbar.setMovable(False)

        button_action = QAction(
            QIcon.fromTheme("preferences-system"), "Your button", self
        )

        button_action.setStatusTip("This is your button")
        button_action.triggered.connect(self.onMyToolBarButtonClick)
        self._toolbar.addAction(button_action)

        self._toolbar.addSeparator()

        # Y-Axis Scale controls
        self._scale_toolbar = QToolBar("Scale Toolbar")
        self._scale_toolbar.setIconSize(QSize(16, 16))
        self._scale_toolbar.setMovable(False)
        # self._autoscale_widget = AutoScaleControlWidget()
        # self._scale_toolbar.addWidget(self._vscale_controller.create_button())
        # self._scale_toolbar.addWidget(self._create_y_scale_toolbar())

        # Trigger controls
        self._trigger_toolbar = QToolBar("Trigger Toolbar")
        self._trigger_toolbar.setMovable(False)
        self._trigger_src_cbox = QComboBox()
        self._trigger_src_cbox.setStatusTip("Trigger Source")
        self._trigger_src_cbox.setToolTip("Trigger Source")
        self._trigger_src_cbox.currentIndexChanged.connect(self._trigger_src_change)
        self._trigger_toolbar.addWidget(self._trigger_src_cbox)
        self._trigger_lvl_txt = QLineEdit()
        self._trigger_lvl_txt.setMaximumWidth(80)
        self._trigger_lvl_txt.setAlignment(Qt.AlignmentFlag.AlignRight)
        double_validator = QDoubleValidator()
        double_validator.setLocale(QLocale.c())
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self._trigger_lvl_txt.setValidator(double_validator)
        self._trigger_lvl_txt.setStatusTip("Trigger Level")
        self._trigger_lvl_txt.setToolTip("Trigger Level")
        self._trigger_lvl_txt.editingFinished.connect(self._trigger_level_edited)
        self._trigger_toolbar.addWidget(self._trigger_lvl_txt)

        trigger_pos_slope_action = QAction(
            qta.icon("mdi6.arrow-up"), "Positive slope", self
        )
        trigger_pos_slope_action.setCheckable(True)
        trigger_pos_slope_action.setStatusTip("Trigger on positive slope")
        trigger_pos_slope_action.changed.connect(self._trigger_slope_changed)
        self._trigger_pos_slope_action = trigger_pos_slope_action
        self._trigger_toolbar.addAction(trigger_pos_slope_action)

        trigger_neg_slope_action = QAction(
            qta.icon("mdi6.arrow-down"), "Negative slope", self
        )
        trigger_neg_slope_action.setCheckable(True)
        trigger_neg_slope_action.setStatusTip("Trigger on negative slope")
        trigger_neg_slope_action.changed.connect(self._trigger_slope_changed)
        self._trigger_neg_slope_action = trigger_neg_slope_action
        self._trigger_toolbar.addAction(trigger_neg_slope_action)

        # self._layout.addWidget(self._toolbar)
        # self.internal_main_window.addToolBar(self._toolbar)
        # self.internal_main_window.addToolBar(self._scale_toolbar)
        # self.internal_main_window.addToolBar(self._trigger_toolbar)
        #
        # self._toolbar_layout.addWidget(self._toolbar)
        # self._toolbar_layout.addWidget(self._scale_toolbar)
        # self._toolbar_layout.addWidget(self._trigger_toolbar)

        self._toolbar_widget.add_toolbar(self._toolbar)
        self._toolbar_widget.add_toolbar(self._scale_toolbar)
        self._toolbar_widget.add_toolbar(self._trigger_toolbar)

    def get_toolbar(self):
        return self._toolbar_widget

    def _trigger_slope_changed(self):
        if self.sender() == self._trigger_pos_slope_action:
            self._trigger_neg_slope_action.setChecked(
                not self._trigger_pos_slope_action.isChecked()
            )
        if self.sender() == self._trigger_neg_slope_action:
            self._trigger_pos_slope_action.setChecked(
                not self._trigger_neg_slope_action.isChecked()
            )

        self._trigger.slope = (
            Trigger.SLOPE_POSITIVE
            if self._trigger_pos_slope_action.isChecked()
            else Trigger.SLOPE_NEGATIVE
        )

    def _trigger_src_change(self, index):
        self._trigger.channel = index

    def onMyToolBarButtonClick(self, s):
        self.export_widget_to_svg(
            self._central_widget, "/home/epupillo/test_export.svg"
        )

    def _update_trigger_level_txt(self, value):
        self._trigger_lvl_txt.setText(f"{value:.3f}")

    def _trigger_level_edited(self):
        new_value = float(self._trigger_lvl_txt.text())
        self._trigger.level = new_value
        self._trigger_bar.setPos((0, new_value))

    def _trigger_level_bar_changed(self, line):
        lvl = line.pos()[1]
        self._trigger.level = lvl
        self._update_trigger_level_txt(lvl)

    def export_widget_to_svg(self, widget, file_path):
        """Exports a given widget's current appearance to an SVG file."""

        # 1. Set up the QSvgGenerator
        generator = QSvgGenerator()
        generator.setFileName(file_path)
        generator.setSize(QSize(widget.width(), widget.height()))
        generator.setViewBox(QRect(0, 0, widget.width(), widget.height()))
        generator.setTitle("Widget SVG Export")
        generator.setDescription("An SVG of a QWidget.")

        # 2. Create a QPainter that will draw on the generator
        painter = QPainter()
        painter.begin(generator)

        # 3. Use the widget's render() method to draw itself onto the painter
        widget.render(painter, QPoint(0, 0))

        # 4. Finish painting
        painter.end()

        print(f"Widget successfully exported to {file_path}")

    @Slot(float, float)
    def on_yrange_changed(self, min_val, max_val):
        if self.sender() == self._view_model:
            self._plot.setYRange(min_val, max_val)

    @Slot(str, object)
    def on_format_changed(self, port, media_info):
        if self.sender() == self._view_model:
            LOGGER.debug(f"Port '{port}' format changed: '{media_info}'")
            self.configure_graph(media_info, False)

    @Slot(str, object)
    def on_data_received(self, port, data):
        if self.sender() != self._view_model:
            return

        LOGGER.debug(f"Port '{port}' received {len(data)} samples")
        self._update_perf.mark_start()

        # self._buf.extend(data)

        # if self._trigger_enabled:
        #    x_idx = self._trigger.get_trigger_idx(self._buf)
        #    self._buf.reduce(x_idx)

        # if len(self._buf) >= self._blocksize:
        #    show_data = self._buf.reduce(self._blocksize)
        # self._yrange.update(show_data, self._active_channels)
        #    for i, ch in enumerate(self._active_channels):
        #        self._curves[i].setData(self._x, show_data[:, ch])

        x_data = data["x_data"]
        y_data = data["y_data"]
        for i, ch in enumerate(self._active_channels):
            self._curves[i].setData(x_data, y_data[:, ch])

        self._plot.setLimits(xMin=np.min(x_data), xMax=np.max(x_data))

        self._update_perf.mark_stop()

    @Slot("QList<int>")
    def set_channel_filter(self, channels_indices):
        # for idx, curve in enumerate(self._curves):
        #    if idx in channels_indices:
        #        curve.show()
        #    else:
        #        curve.hide()
        self._active_channels = channels_indices
        # self._cursor1.update_channels()
        # self._cursor2.update_channels()

    @Slot(bool)
    def set_legend_state(self, new_state):
        if new_state:
            self._legend.setParentItem(self._plot.graphicsItem())
        else:
            self._plot.scene().removeItem(self._legend)

    # def set_scale_mode(self, mode: ScaleMode, ranges=None):
    #    # self._yrange.set_mode(mode, ranges)
    #    self._yrange.mode = mode
    #    self._yrange.range = ranges

    # def set_yrange(self, min_val, max_val):
    #    self._yrange.set_manual_range(min_val, max_val)

    def set_trigger_mode(self, new_mode: bool):
        self._trigger_enabled = new_mode
        self._trigger_bar.setVisible(new_mode)
        self._trigger_toolbar.setVisible(new_mode)

    # @property
    # def y_axis_scale_mode(self):
    #    return self._yrange.mode
