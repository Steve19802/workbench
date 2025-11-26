import logging
from dvg_ringbuffer import RingBuffer
import numpy as np
from time import perf_counter
from blinker import Signal

from workbench.contracts.enums import ScaleMode

LOGGER = logging.getLogger(__name__)


class ScaleController:
    """
    Manages the Y-axis scaling of a plot with multiple modes.
    Emits a PySide6 Signal when the range should be updated.
    """

    
    def __init__(self):
        # It will emit two float arguments: min_val and max_val.
        self.range_changed = Signal()
        self.state_updated = Signal()

        # --- Internal State ---
        self._mode = ScaleMode.AUTOMATIC
        self._manual_min = -1.0
        self._manual_max = 1.0
        self._auto_ranges = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
        self._smoothing = 5

        self._range_buffer = RingBuffer(self._smoothing)
        self._current_range_index = -1
        self._last_range_change_ts = -1

        self._current_auto_min = None
        self._current_auto_max = None

    # --- Public Properties ---

    @property
    def mode(self) -> ScaleMode:
        return self._mode

    @mode.setter
    def mode(self, new_mode: ScaleMode):
        if self._mode == new_mode:
            return
        LOGGER.debug(f"ScaleController mode set to: {new_mode.value}")
        self._mode = new_mode
        self._reset_auto_state()

        if self._mode == ScaleMode.MANUAL:
            # Use .emit() for Qt Signals
            self.range_changed.send(self, min=self._manual_min, max=self._manual_max)
        self.state_updated.send(self)

    @property
    def manual_min(self) -> float:
        return self._manual_min

    @manual_min.setter
    def manual_min(self, value: float):
        self._manual_min = value
        # Setting a manual value still switches mode
        self.mode = ScaleMode.MANUAL
        self.range_changed.send(self, min=self._manual_min, max=self._manual_max)

    @property
    def manual_max(self) -> float:
        return self._manual_max

    @manual_max.setter
    def manual_max(self, value: float):
        self._manual_max = value
        self.mode = ScaleMode.MANUAL
        self.range_changed.send(self, min=self._manual_min, max=self._manual_max)

    # --- Public Methods ---
    def update(self, data: np.ndarray):
        if self._mode == ScaleMode.AUTOMATIC:
            self._calculate_automatic_limits(data)
        elif self._mode == ScaleMode.AUTO_RANGE:
            self._calculate_auto_range(data)

    # --- Internal Logic  ---

    def _reset_auto_state(self):
        """Resets the state tracking for automatic modes."""
        self._current_auto_min = None
        self._current_auto_max = None
        self._current_range_index = -1
        self._range_buffer = RingBuffer(self._smoothing)

    def _calculate_auto_range(self, data: np.ndarray):
        max_val = np.max(np.abs(data))
        range_idx = (np.abs(self._auto_ranges - max_val)).argmin()

        self._range_buffer.append(range_idx)
        # Use mean instead of average for clarity with numpy
        smoothed_range_idx = int(np.round(np.mean(list(self._range_buffer))))

        delta_t = perf_counter() - self._last_range_change_ts
        if smoothed_range_idx != self._current_range_index and delta_t > 1.0:
            new_range = self._auto_ranges[smoothed_range_idx]
            self.range_changed.send(self, min=-new_range, max=new_range)
            self._current_range_index = smoothed_range_idx
            self._last_range_change_ts = perf_counter()

    def _calculate_automatic_limits(self, data: np.ndarray):
        max_val = np.max(data)
        min_val = np.min(data)

        # On first run, set the limits and update immediately
        if self._current_auto_max is None or self._current_auto_min is None:
            self._current_auto_max = max_val
            self._current_auto_min = min_val
            self.range_changed.send(self, min=min_val, max=max_val)
            return

        # Check if new data exceeds current limits by a certain threshold
        # (This logic can be tuned as needed)
        max_dev = (max_val - self._current_auto_max) / (self._current_auto_max or 1)
        min_dev = (min_val - self._current_auto_min) / (self._current_auto_min or 1)

        if max_dev > 0.2 or min_dev < -0.2:
            self.range_changed.send(self, min=min_val, max=max_val)
            self._current_auto_min = min_val
            self._current_auto_max = max_val
