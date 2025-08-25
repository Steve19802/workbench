from __future__ import annotations
from enum import Enum
import logging

from blinker import Signal
from ..media_info import MediaInfo
from ..base_blocks import Block
from ..helpers.scale_controller import ScaleController, ScaleMode

LOGGER = logging.getLogger(__name__)


class Scope(Block):
    vertical_range_changed = Signal()
    vertical_scale_mode_changed = Signal()

    class Modes(Enum):
        TIME = "Time"
        SPECTRUM = "Spectrum"
        XY = "XY"

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self.PORT_NAME = "in"

        self.add_input_port(self.PORT_NAME)

        self._mode: Scope.Modes = Scope.Modes.TIME
        self._yscale_controller = ScaleController()

        self._yscale_controller.range_changed.connect(self._on_yscale_range_changed)
        self._yscale_controller.state_updated.connect(self._on_yscale_mode_changed)

        self._channels_visibility = {}

    def _on_yscale_range_changed(self, sender, min, max):
        self.vertical_range_changed.send(self, min=min, max=max)

    def _on_yscale_mode_changed(self, sender):
        self.vertical_scale_mode_changed.send(self)

    def on_input_received(self, port_name: str, data) -> None:
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

        # Call the super method to pass the full dataset up
        super().on_input_received(port_name, data)

    def on_format_received(self, port_name: str, media_info: MediaInfo) -> None:
        # Handle the channels visibility state
        updated_visibility = {}
        for channel_info in media_info.channels:
            name = channel_info.name
            # If we have seen this channel before, keep its existing setting.
            # Otherwise, default the new channel to be visible (True)
            updated_visibility[name] = self._channels_visibility.get(name, True)

        self._channels_visibility = updated_visibility

        # Let the base object to process the format and emit the corresponding signal
        super().on_format_received(port_name, media_info)

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
