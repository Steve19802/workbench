import numpy as np
from threading import Lock
import logging

from ..base_blocks import Block
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports
from ..media_info import MediaInfo

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in-db"], outputs=["out-db"])
class OctaveSmoother(Block):
    """
    Smooths a linear RMS frequency spectrum using Fractional Octave Smoothing.
    
    Input: Linear RMS Amplitude (e.g., from FFTAnalyzer 'out-abs-rms')
    Output: Smoothed Spectrum in dB
    
    Algorithm:
    1. Converts RMS to Power (RMS^2)
    2. Applies Variable-Width Smoothing on Power (preserves energy)
    3. Converts Result to dB
    """

    def __init__(self, name: str, bandwidth: float = 0.333) -> None:
        super().__init__(name)
        
        self._bandwidth = bandwidth
        self._lock = Lock()
        
        self._window_left_indices = None
        self._window_right_indices = None
        self._window_sizes = None
        self._n_bins = 0

    def on_format_received(self, port_name: str, media_info: MediaInfo):
        with self._lock:
            self._n_bins = media_info.blocksize
            
            out_info = media_info.copy()
            out_info.name = self.name
            self.set_port_format("out-db", out_info)
            
            # --- PRE-CALCULATION (Same as before) ---
            bin_indices = np.arange(self._n_bins)
            
            # Calculate relative width
            alpha = (2**(self._bandwidth/2)) - (2**(-self._bandwidth/2))
            widths = bin_indices * alpha
            
            # Enforce minimum width of 3 bins to ensure low-freq smoothing happens
            widths = np.maximum(widths, 3.0)
            
            half_widths = np.floor(widths / 2).astype(int)
            
            left_indices = bin_indices - half_widths
            right_indices = bin_indices + half_widths
            
            # --- FIX: DC PROTECTION ---
            # For all bins > 0, ensure the window NEVER includes Bin 0 (DC).
            # We clamp the left index to be at least 1.
            # (Bin 0 itself is allowed to look at Bin 0)
            left_indices[1:] = np.maximum(left_indices[1:], 1)
            # ---------------------------
            
            self._window_left_indices = np.clip(left_indices, 0, self._n_bins - 1)
            self._window_right_indices = np.clip(right_indices, 0, self._n_bins - 1)
            
            self._window_sizes = (self._window_right_indices - self._window_left_indices) + 1
            #self._window_sizes[self._window_sizes == 0] = 1
            
            LOGGER.debug(f"{self.name}: Pre-calculated octave windows for {self._n_bins} bins")

    def on_input_received(self, port_name: str, data: np.ndarray):
        if self._window_sizes is None:
            return

        n_channels = data.shape[1]
        output = np.zeros_like(data)
        
        # --- OPTIMIZED PROCESSING ---
        
        # 1. Convert RMS Amplitude to Linear Power
        #    Power = Amplitude^2
        #power_spectrum = data**2
        
        # Clamp to -160dB to prevent underflow/weirdness with silence
        data_clamped = np.maximum(data, -160.0)
        power_spectrum = 10.0**(data_clamped / 10.0)

        for ch in range(n_channels):
            channel_power = power_spectrum[:, ch]
            
            # 2. Integral Array on POWER
            #    Handle NaNs (replace with 0 energy)
            channel_power = np.nan_to_num(channel_power, nan=0.0, posinf=0.0, neginf=0.0)
            integral = np.cumsum(channel_power)
            
            # 3. Calculate Sums using Window Indices
            right_sums = integral[self._window_right_indices]
            
            left_vals_indices = self._window_left_indices - 1
            left_sums = np.zeros_like(right_sums)
            valid_mask = left_vals_indices >= 0
            left_sums[valid_mask] = integral[left_vals_indices[valid_mask]]
            
            # 4. Average Power
            window_sums = right_sums - left_sums
            avg_power = window_sums / self._window_sizes
            
            # 5. Convert Average Power directly to dB
            #    dB = 10 * log10(Power)
            #    (Note: 10*log because it's Power. If it were amplitude it would be 20*log)
            output[:, ch] = 10.0 * np.log10(avg_power + 1e-20)
            
        self.send_port_data("out-db", output)

    @property
    def bandwidth(self) -> float:
        return self._bandwidth

    @bandwidth.setter
    def bandwidth(self, value: float):
        with self._lock:
            self._bandwidth = max(0.01, value)
            # Note: In a live graph, you'd want to force a recalc here
            # by re-running the on_format_received logic if self._n_bins > 0

    def on_start(self):
        return True

    def on_stop(self):
        return True
