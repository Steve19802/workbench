import logging
import numpy as np
from PySide6.QtCore import Signal, Slot

from workbench.contracts.enums import ScopeModes, TriggerSlope
from workbench.core.blocks.scope_block import Scope
from .node_viewmodel import NodeViewModel

import traceback

LOGGER = logging.getLogger(__name__)


class ScopeViewModel(NodeViewModel):
    view_input_format_changed = Signal(str, object)
    view_data_received = Signal(str, object)
    view_vertical_range_changed = Signal(float, float)
    view_vertical_scale_mode_changed = Signal()

    def __init__(self, model: Scope, dock_widget):
        super().__init__(model)

        LOGGER.info(f"model: {model}")

        self._dock_widget = dock_widget

        self._media_info = None

        self.model.input_format_changed.connect(self.on_model_input_format_changed)
        self.model.data_received.connect(self.on_model_data_received)

        self.model.vertical_range_changed.connect(self.on_ycontroller_range_changed)
        self.model.vertical_scale_mode_changed.connect(
            self.on_ycontroller_state_changed
        )

        self._dock_widget.bind_view_model(self)

        self._last_data_length = 0
        self._last_xdata = None

    def on_model_input_format_changed(self, sender, **kwargs):
        port_name = kwargs.get("port_name")
        media_info = kwargs.get("media_info")

        self._media_info = media_info

        self.view_input_format_changed.emit(port_name, media_info)

    def _generate_x_axis(self, data_len):

        # Generate the corresponding time vector (x-axis)
        if self.model.mode == ScopeModes.TIME:
            duration = float(data_len - 1) / (
                self._media_info.samplerate if self._media_info else 1
            )
            x_data = np.linspace(0, duration, num=data_len)
            self._last_data_length = data_len
        elif self.model.mode == ScopeModes.SPECTRUM:
            nyquist = self._media_info.metadata.get('nyquist', 24000.0)
            x_data = np.linspace(0, nyquist, num=data_len)
        else:
            LOGGER.error(f"{self.model.mode} NOT IMPLEMENTED!!!")


        self._last_xdata = x_data
        

    def on_model_data_received(self, sender, **kwargs):
        port_name = kwargs.get("port_name")
        data = kwargs.get("data")
        data_len = len(data)

        # If we don't have any valid data we can't do anything
        if data is None:
            return

        #LOGGER.info(f"port_name: {port_name}, data_len: {np.shape(data)}, data: {data}")
        if self._last_data_length != data_len:
            # Generate the corresponding time vector (x-axis)
            #duration = float(data_len - 1) / (
            #    self._media_info.samplerate if self._media_info else 1
            #)
            #x_data = np.linspace(0, duration, num=data_len)
            #self._last_data_length = data_len
            #self._last_xdata = x_data
            self._generate_x_axis(data_len)

        # Prepare payload for sending to the view
        payload = {"x_data": self._last_xdata, "y_data": data}

        # Notify the view that we have new data to show
        self.view_data_received.emit(port_name, payload)

    @Slot(float, float)
    def on_ycontroller_range_changed(self, sender, min, max):
        self.view_vertical_range_changed.emit(min, max)

    @Slot()
    def on_ycontroller_state_changed(self, sender):
        self.view_vertical_scale_mode_changed.emit()

    def show_window(self):
        self._dock_widget.toggleView(True)

    def cleanup(self):
        LOGGER.debug("Cleaning up dock widget")
        self._dock_widget.deleteDockWidget()
