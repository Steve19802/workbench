import numpy as np
from blinker import Signal

from workbench.contracts.enums import TriggerSlope


class TriggerController:
    """
    Manages trigger state and provides the logic to find a trigger index in data.
    """

    # Signal to announce that one of its settings has changed.
    settings_changed = Signal()

    def __init__(self):
        self._level = 0.5
        self._slope = TriggerSlope.POSITIVE
        self._channel = 0

    # --- Public Properties for State Management ---

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, value: float):
        if self._level != value:
            self._level = value
            self.settings_changed.send(self)

    @property
    def slope(self) -> TriggerSlope:
        return self._slope

    @slope.setter
    def slope(self, value: TriggerSlope):
        if self._slope != value:
            self._slope = value
            self.settings_changed.send(self)

    @property
    def channel(self) -> int:
        return self._channel

    @channel.setter
    def channel(self, value: int):
        if self._channel != value:
            self._channel = value
            self.settings_changed.send(self)

    # --- Public Logic Method ---

    def get_trigger_index(self, data: np.ndarray) -> int:
        """
        Calculates and returns the trigger index for the given data
        based on the current settings.
        """
        # Guard against empty or invalid data
        if data.shape[0] == 0 or self.channel >= data.shape[1]:
            return 0

        active_channel_data = data[:, self.channel]

        if self.level > np.max(np.abs(active_channel_data)):
            return 0

        # Trigger logic
        data_diff = np.diff(active_channel_data, prepend=active_channel_data[0])
        data_slope = (
            (data_diff < 0) if self.slope == TriggerSlope.POSITIVE else (data_diff > 0)
        )
        trigger_idx = np.argmin(
            np.abs(active_channel_data - self.level + data_slope * 10)
        )

        return int(trigger_idx)
