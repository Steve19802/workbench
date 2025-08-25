import logging
from PySide6.QtCore import Signal, Slot

from workbench.core.blocks.scope_block import Scope
from .node_viewmodel import NodeViewModel

LOGGER = logging.getLogger(__name__)


class ScopeViewModel(NodeViewModel):
    view_input_format_changed = Signal(str, object)
    view_data_received = Signal(str, object)
    view_vertical_range_changed = Signal(float, float)
    view_vertical_scale_mode_changed = Signal()

    def __init__(self, model: Scope, dock_widget):
        super().__init__(model)

        self._dock_widget = dock_widget

        self.model.input_format_changed.connect(self.on_model_input_format_changed)
        self.model.data_received.connect(self.on_model_data_received)

        self.model.vertical_range_changed.connect(self.on_ycontroller_range_changed)
        self.model.vertical_scale_mode_changed.connect(
            self.on_ycontroller_state_changed
        )

        self._dock_widget.bind_view_model(self)

    def on_model_input_format_changed(self, sender, **kwargs):
        port_name = kwargs.get("port_name")
        media_info = kwargs.get("media_info")

        self.view_input_format_changed.emit(port_name, media_info)

    def on_model_data_received(self, sender, **kwargs):
        port_name = kwargs.get("port_name")
        data = kwargs.get("data")

        self.view_data_received.emit(port_name, data)

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
