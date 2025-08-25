import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum

from workbench.core.blocks import SignalGenerator


LOGGER = logging.getLogger(__name__)


class SignalGeneratorNode(NodeGraphQt.BaseNode):
    """
    A node for representing an Audio Signal Generator.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Signal Generator"

    def __init__(self):
        super(SignalGeneratorNode, self).__init__()
        self._view_model = None

    def bind_view_model(self, view_model):
        self._view_model = view_model
        self._view_model.view_property_changed.connect(
            self.on_view_model_property_changed
        )

        for out_port_name in self._view_model.get_output_ports():
            self.add_output(out_port_name)

        for in_port_name in self._view_model.get_input_ports():
            self.add_input(in_port_name)

        self.create_property(
            "frequency",
            value=self._view_model.get_property("frequency"),
            range=(0, 22000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select frequency",
        )

        self.create_property(
            "amplitude",
            value=self._view_model.get_property("amplitude"),
            range=(0, 50.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select amplitude",
        )

        self.create_property(
            "samplerate",
            value=self._view_model.get_property("samplerate"),
            range=(0, 192000),
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select input samplerate",
        )

        self.create_property(
            "blocksize",
            value=self._view_model.get_property("blocksize"),
            range=(0, 192000),
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select input block size",
        )

    def get_view_model(self):
        return self._view_model

    def set_property(self, name, value, push_undo=True):
        LOGGER.debug(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)
        if self._view_model:
            self._view_model.update_property(name, value)

    def on_view_model_property_changed(self, name, value):
        if self.has_property(name):
            super().set_property(name, value, push_undo=False)


class SignalGeneratorNodeOld(NodeGraphQt.BaseNode):
    """
    A node for representing an Audio Signal Generator.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Signal Generator"

    def __init__(self):
        super(SignalGeneratorNodeOld, self).__init__()
        self.backend = SignalGenerator(self.name())

        for out_port_name in self.backend.get_output_ports():
            self.add_output(out_port_name)

        for in_port_name in self.backend.get_input_ports():
            self.add_input(in_port_name)

        self.create_property(
            "frequency",
            value=self.backend.frequency,
            range=(0, 22000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select frequency",
        )

        self.create_property(
            "amplitude",
            value=self.backend.amplitude,
            range=(0, 50.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select amplitude",
        )

        self.create_property(
            "sample_rate",
            value=self.backend.samplerate,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="Select input samplerate",
        )

        self.create_property(
            "block_size",
            value=self.backend.blocksize,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="Select input block size",
        )

    def get_backend(self):
        return self.backend

    def set_property(self, name, value, push_undo=True):
        print(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)
        if name == "amplitude":
            self.backend.amplitude = value
        if name == "frequency":
            self.backend.frequency = value
        elif name == "channels":
            self.backend.channels = int(value)
        elif name == "sample_rate":
            self.backend.samplerate = int(value)
        elif name == "block_size":
            self.backend.blocksize = int(value)
