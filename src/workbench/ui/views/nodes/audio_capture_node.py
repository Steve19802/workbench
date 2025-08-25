import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum

from workbench.core.blocks.audio_capture import AudioCapture


LOGGER = logging.getLogger(__name__)


class AudioCaptureNode(NodeGraphQt.BaseNode):
    """
    A node for representing a AudioCapture.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Audio Capture"

    def __init__(self):
        super(AudioCaptureNode, self).__init__()
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

        sound_devices = self._view_model.get_property("devices")
        input_devices = [
            f"{d['name']} - input channels: {d['max_input_channels']}"
            for d in sound_devices
        ]
        input_channels = [
            f"{ch}"
            for ch in range(
                1,
                sound_devices[self._view_model.get_property("device")][
                    "max_input_channels"
                ]
                + 1,
            )
        ]

        self.create_property(
            "input_device",
            value=input_devices[self._view_model.get_property("device")],
            items=input_devices,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select input device",
        )

        self.create_property(
            "channels",
            value=str(self._view_model.get_property("channels")),
            items=input_channels,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select input channels",
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

        self.create_property(
            "calibration_factor",
            value=self._view_model.get_property("calibration_factor"),
            range=(0, 50.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Set the calibration factor",
        )

    def update_channels(self):
        LOGGER.debug(f"update channels for {self.get_property('input_device')}")
        input_device = self.get_property("input_device")

        if self._view_model:
            sound_devices = self._view_model.get_property("devices")
        else:
            sound_devices = []
        input_devices = [
            f"{d['name']} - input channels: {d['max_input_channels']}"
            for d in sound_devices
        ]
        input_device_index = [
            i for i, dev in enumerate(input_devices) if dev == input_device
        ]
        if len(input_device_index) > 0:
            input_channels = [
                f"{ch}"
                for ch in range(
                    1, sound_devices[input_device_index[0]]["max_input_channels"] + 1
                )
            ]
            self.model.set_items("channels", input_channels)
            if self.graph:
                self.graph.property_cfg_changed.emit(self, "channels")

    def get_view_model(self):
        return self._view_model

    def set_property(self, name, value, push_undo=True):
        print(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)
        if self._view_model:
            if name == "input_device":
                self._view_model.update_property("device", value.split("-")[0].strip())
            else:
                self._view_model.update_property(name, value)

    def on_view_model_property_changed(self, name, value):
        if name == "device":
            self.update_channels()
        if self.has_property(name):
            super().set_property(name, value, push_undo=False)


class AudioCaptureNode2(NodeGraphQt.BaseNode):
    """
    A node for representing a AudioCapture.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Audio Capture"

    def __init__(self):
        super(AudioCaptureNode2, self).__init__()
        self.backend = AudioCapture(self.name())

        for out_port_name in self.backend.get_output_ports():
            self.add_output(out_port_name)

        for in_port_name in self.backend.get_input_ports():
            self.add_input(in_port_name)

        sound_devices = AudioCapture.get_audio_devices()
        input_devices = [
            f"{d['name']} - input channels: {d['max_input_channels']}"
            for d in sound_devices
        ]
        input_channels = [
            f"{ch}"
            for ch in range(1, sound_devices[self.backend.device]["max_input_channels"])
        ]

        self.create_property(
            "input_device",
            value=str(input_devices[self.backend.device]),
            items=input_devices,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select input device",
        )

        self.create_property(
            "channels",
            value=str(self.backend.channels),
            items=input_channels,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select input channels",
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

    def update_channels(self):
        LOGGER.debug(f"update channels for {self.get_property('input_device')}")
        input_device = self.get_property("input_device")

        sound_devices = AudioCapture.get_audio_devices()
        input_devices = [
            f"{d['name']} - input channels: {d['max_input_channels']}"
            for d in sound_devices
        ]
        input_device_index = [
            i for i, dev in enumerate(input_devices) if dev == input_device
        ]
        if len(input_device_index) > 0:
            input_channels = [
                f"{ch}"
                for ch in range(
                    1, sound_devices[input_device_index[0]]["max_input_channels"] + 1
                )
            ]
            self.model.set_items("channels", input_channels)
            if self.graph:
                self.graph.property_cfg_changed.emit(self, "channels")

    def get_backend(self):
        return self.backend

    def set_property(self, name, value, push_undo=True):
        print(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)
        if name == "input_device":
            self.backend.device = value.split("-")[0].strip()
            self.update_channels()
        elif name == "channels":
            self.backend.channels = int(value)
        elif name == "sample_rate":
            self.backend.samplerate = int(value)
        elif name == "block_size":
            self.backend.blocksize = int(value)
