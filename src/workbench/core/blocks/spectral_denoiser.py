import numpy as np
from scipy.signal import savgol_filter
from threading import Lock
import logging

from ..base_blocks import Block
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports
from ..media_info import MediaInfo

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in-db"], outputs=["out-clean"])
class SpectralDenoiser(Block):
    """
    Removes visual 'hash' or noise from a spectrum trace without 
    distorting the overall shape.
    
    Uses a Savitzky-Golay filter, which fits a polynomial to the data.
    This is similar to a 'Video Filter' on a hardware analyzer.
    """

    def __init__(self, name: str, strength: int = 1) -> None:
        """
        Args:
            strength: A factor (1-50) that controls the window length.
                      Higher = smoother trace, but may blur sharp peaks.
        """
        super().__init__(name)
        
        self._strength = strength
        self._lock = Lock()
        self._window_len = 5 # Calculated from strength
        self._poly_order = 2 # 2nd order polynomial follows curves well
        self._n_bins = 0

    def on_format_received(self, port_name: str, media_info: MediaInfo):
        with self._lock:
            self._n_bins = media_info.blocksize
            
            out_info = media_info.copy()
            out_info.name = self.name
            self.set_port_format("out-clean", out_info)
            
            self._update_filter_params()

    def _update_filter_params(self):
        """
        Calculates the SavGol window length based on strength.
        Window length must be odd and greater than poly_order.
        """
        # Map strength (1-50) to window size (5 - 101 bins)
        # This is a linear mapping for simplicity
        raw_len = 3 + (self._strength * 2)
        
        # Ensure it's odd
        if raw_len % 2 == 0:
            raw_len += 1
            
        self._window_len = raw_len
        LOGGER.debug(f"{self.name}: Filter window set to {self._window_len} bins")

    def on_input_received(self, port_name: str, data: np.ndarray):
        if self._n_bins == 0:
            return

        n_channels = data.shape[1]
        output = np.zeros_like(data)
        
        # We process the dB data DIRECTLY. 
        # We are smoothing the TRACE, not averaging the ENERGY.
        
        try:
            for ch in range(n_channels):
                trace = data[:, ch]
                
                # --- DC PROTECTION ---
                # We EXCLUDE the DC bin (index 0) from the filter.
                # If we include it, the massive negative value at DC will
                # drag down the low frequencies.
                trace_no_dc = trace[1:]
                
                # Apply Savitzky-Golay Filter
                # mode='interp' handles the edges gracefully
                smoothed_trace = savgol_filter(
                    trace_no_dc, 
                    window_length=self._window_len, 
                    polyorder=self._poly_order,
                    mode='interp'
                )
                
                # Reconstruct
                output[0, ch] = trace[0] # Pass DC through
                output[1:, ch] = smoothed_trace
                
        except Exception as e:
            # Fallback if window is too large for data size
            LOGGER.error(f"{self.name}: Filter error: {e}")
            output = data 

        self.send_port_data("out-clean", output)

    @property
    def strength(self) -> int:
        return self._strength

    @strength.setter
    def strength(self, value: int):
        with self._lock:
            self._strength = max(1, min(100, value))
            self._update_filter_params()

    def on_start(self):
        return True

    def on_stop(self):
        return True
