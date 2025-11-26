from __future__ import annotations
from enum import Enum
import logging
import numpy as np
from math import ceil

from blinker import Signal


from workbench.contracts.enums import ScopeModes, TriggerSlope
from workbench.core.helpers.media_ring_buffer import MediaRingBuffer
from workbench.core.helpers.trigger_controller import TriggerController
from ..media_info import MediaInfo
from ..base_blocks import Block
from ..helpers.scale_controller import ScaleController, ScaleMode
from ..helpers.auto_coerce_enum import auto_coerce_enum
from ..helpers.not_serializable_decorator import not_serializable
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

LOGGER = logging.getLogger(__name__)

LOGGER.setLevel("DEBUG")

@register_block
@define_ports(inputs=["in"])
class Scope(Block):
    vertical_range_changed = Signal()
    vertical_scale_mode_changed = Signal()
    trigger_setting_changed = Signal()

    def __init__(self, name: str) -> None:
        super().__init__(name)


        self.add_input_port(self.PORT_NAME)
        self.PORT_NAME = "in"

        self._buffer = None
        self._buffer_size = 0
        self._timespan = 1
        self._blocksize = 0
        self._is_buffer_invalid = True

        self._mode: ScopeModes = ScopeModes.TIME
        self._yscale_controller = ScaleController()

        self._yscale_controller.range_changed.connect(self._on_yscale_range_changed)
        self._yscale_controller.state_updated.connect(self._on_yscale_mode_changed)

        self._trigger_controller = TriggerController()
        self._trigger_controller.settings_changed.connect(
            self._on_trigger_settings_changed
        )

        self._channels_visibility = {}

    def _create_buffer(self):
        input_media_info = self.get_input_port("in").media_info
        in_samplerate = input_media_info.samplerate
        in_blocksize = input_media_info.blocksize
        blocksize = ceil(self._timespan * in_samplerate)
        buffer_size = (
            in_blocksize * ceil(self._timespan * in_samplerate / in_blocksize)
            + in_blocksize
        )
        LOGGER.debug(f"Creating buffer of {buffer_size} samples")
        self._buffer_size = buffer_size
        self._blocksize = blocksize
        self._buffer = MediaRingBuffer(buffer_size, input_media_info.dtype, False)
        self._is_buffer_invalid = False

    def _on_yscale_range_changed(self, sender, min, max):
        self.vertical_range_changed.send(self, min=min, max=max)

    def _on_yscale_mode_changed(self, sender):
        self.vertical_scale_mode_changed.send(self)

    def _on_trigger_settings_changed(self, sender):
        self.trigger_setting_changed.send(self)

    def on_input_received(self, port_name: str, data) -> None:
        if self._is_buffer_invalid:
            self._create_buffer()

        # Get the indices of the currently visible channels.
        visible_indices = [
            idx
            for idx, name in enumerate(self.channel_names)
            if self._channels_visibility.get(name, False)
        ]

        # If there are any visible channels, create a view of the data
        # containing only those channels.
        if visible_indices:
            visible_data = data[:, visible_indices]

            # Pass ONLY the filtered data to the scale controller.
            self._yscale_controller.update(visible_data)

        self._buffer.extend(data)
        if len(self._buffer) >= self._blocksize:
            # extract required data from buffer
            out_data = np.array(self._buffer[: self._blocksize])
        else:
            out_data = np.array(self._buffer)

        # Call the super method to pass the full dataset up
        super().on_input_received(port_name, out_data)

        if len(self._buffer) >= self._buffer_size:
            port = self.get_input_port(port_name)
            blocksize = port.media_info.blocksize if port and port.media_info else 2048
            self._buffer.reduce(blocksize)

    def on_format_received(self, port_name: str, media_info: MediaInfo) -> None:
        # create infput buffer based on the received format
        self._create_buffer()

        # Handle the channels visibility state
        updated_visibility = {}
        for channel_info in media_info.channels:
            name = channel_info.name
            # If we have seen this channel before, keep its existing setting.
            # Otherwise, default the new channel to be visible (True)
            updated_visibility[name] = self._channels_visibility.get(name, True)

        self._channels_visibility = updated_visibility

        scope_media_info = media_info.copy()
        scope_media_info.blocksize = self._blocksize

        # Let the base object to process the format and emit the corresponding signal
        super().on_format_received(port_name, scope_media_info)

    @property
    def mode(self) -> Scope.Modes:
        return self._mode

    @mode.setter
    def mode(self, new_mode: Scope.Modes):
        self._mode = new_mode
        self.on_property_changed("mode", new_mode)

    @property
    def vertical_scale_mode(self) -> ScaleMode:
        return self._yscale_controller.mode

    @vertical_scale_mode.setter
    def vertical_scale_mode(self, new_mode: ScaleMode) -> None:
        self._yscale_controller.mode = new_mode
        self.on_property_changed("vertical_scale_mode", new_mode)

    @property
    def vertical_scale_min(self) -> float:
        return self._yscale_controller.manual_min

    @vertical_scale_min.setter
    def vertical_scale_min(self, min_value) -> None:
        self._yscale_controller.manual_min = min_value
        self.on_property_changed("vertical_scale_min", min_value)
        self.on_property_changed("vertical_scale_mode", self._yscale_controller.mode)

    @property
    def vertical_scale_max(self) -> float:
        return self._yscale_controller.manual_max

    @vertical_scale_max.setter
    def vertical_scale_max(self, max_value) -> None:
        self._yscale_controller.manual_max = max_value
        self.on_property_changed("vertical_scale_max", max_value)
        self.on_property_changed("vertical_scale_mode", self._yscale_controller.mode)

    @property
    def channels_visibility(self) -> dict:
        """Returns a copy of the current channels visibility map."""
        return self._channels_visibility.copy()

    @property
    def channel_names(self) -> list:
        """Returns the ordered list of channel names."""

        # Get input port.
        port = self.get_input_port(self.PORT_NAME)
        if port is None:
            return []

        # Get port media info
        media_info = port.media_info
        if media_info is None:
            return []

        # return list of channels name
        return [channel_info.name for channel_info in media_info.channels]

    @property
    def trigger_level(self) -> float:
        return self._trigger_controller.level

    @trigger_level.setter
    def trigger_level(self, value: float):
        self._trigger_controller.level = value

    @property
    def trigger_slope(self) -> TriggerSlope:
        return self._trigger_controller.slope

    @trigger_slope.setter
    def trigger_slope(self, value: TriggerSlope):
        self._trigger_controller.slope = value

    @property
    def trigger_channel(self) -> int:
        return self._trigger_controller.channel

    @trigger_channel.setter
    def trigger_channel(self, value: int):
        self._trigger_controller.channel = value

    def set_channel_visible(self, channel_name: str, visible: bool):
        """Allows the ViewModel to update the visibility of a channel."""
        if channel_name in self._channels_visibility:
            if self._channels_visibility[channel_name] != visible:
                self._channels_visibility[channel_name] = visible
                # Announce that a specific property has changed
                self.property_changed.send(
                    self, name="channel_visibility", value=self.channels_visibility
                )
        else:
            LOGGER.error(
                f"Attempted to set visibility for unknown channel: {channel_name}"
            )

    @property
    def time_span(self) -> float:
        return self._timespan

    @time_span.setter
    def time_span(self, span: float):
        LOGGER.debug(f"New timespan is {span}")
        if span != self._timespan:
            self._timespan = span
            self.property_changed.send(self, name="time_span", value=span)
            self._is_buffer_invalid = True
