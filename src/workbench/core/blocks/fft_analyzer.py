import numpy as np
from scipy.fft import rfft
from scipy.signal import get_window

from workbench.contracts.enums import FFTWindow
from threading import Condition, Thread, Lock
from ..media_blocks import Block
from ..media_info import MediaInfo, ChannelInfo
from ..helpers.media_ring_buffer import MediaRingBuffer
from ..helpers.auto_coerce_enum import auto_coerce_enum
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

import logging

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in"], outputs=["out-abs-peak", "out-db-peak", "out-abs-rms", "out-db-rms"])
class FFTAnalyzer(Block):
    def __init__(
        self,
        name: str,
        fft_size: int = 4096,
        fft_window=FFTWindow.BLACKMAN_HARRIS,
        fft_overlap: int = 0,
    ) -> None:
        super().__init__(name)

        # Internal attributes
        self._fft_size = fft_size
        self._fft_overlap = fft_overlap
        self._fft_window = fft_window

        self._window_array = None
        self._coherent_gain = 1.0
        self._noise_power_gain = 1.0  # Sum of squares

        self._fft_scaling_peak = None
        self._fft_scaling_rms = None

        self._buffer = None
        self._condition = Condition()

        # Synchronization objects
        self._lock = Lock()


        self._create_window()

        LOGGER.debug(f"name: {name}, fft_size: {fft_size}")

    def _update_media_info(self):
        input_media_info = self.get_input_port("in").media_info

        # Create a base MediaInfo for all outputs
        output_media_info = MediaInfo()
        output_media_info.name = self.name
        output_media_info.samplerate = input_media_info.samplerate / self._fft_size
        output_media_info.dtype = (np.float64, input_media_info.channels_number())
        output_media_info.blocksize = self._fft_size // 2 + 1
        output_media_info.channels = [
            ChannelInfo(name=f"X[{ch.name}]", dtype=np.float64)
            for ch in input_media_info.channels
        ]

        # Add all relevant FFT metadata for downstream blocks
        output_media_info.metadata['domain'] = 'frequency'
        output_media_info.metadata["fft_size"] = self._fft_size
        output_media_info.metadata["window_type"] = self._fft_window.value
        output_media_info.metadata["coherent_gain"] = self._coherent_gain
        output_media_info.metadata["noise_power_gain"] = self._noise_power_gain
        output_media_info.metadata["audio_samplerate"] = input_media_info.samplerate
        output_media_info.metadata['nyquist'] = input_media_info.samplerate / 2.0

        # Set format for all output ports
        self.set_port_format("out-abs-peak", output_media_info)
        self.set_port_format("out-db-peak", output_media_info.copy())
        self.set_port_format("out-abs-rms", output_media_info.copy())
        self.set_port_format("out-db-rms", output_media_info.copy())

    def _create_buffer(self):
        input_media_info = self.get_input_port("in").media_info
        in_blocksize = input_media_info.blocksize
        buffer_size = 2 * (self._fft_size + in_blocksize)
        self._buffer = MediaRingBuffer(buffer_size, input_media_info.dtype, False)

    def _create_window(self):
        # Map our enum to the names used by scipy.signal.get_window
        if self._fft_window == FFTWindow.RECTANGULAR:
            window_name = "boxcar"
        elif self._fft_window == FFTWindow.BLACKMAN_HARRIS:
            window_name = "blackmanharris"
        elif self._fft_window == FFTWindow.FLAT_TOP:
            window_name = "flattop"
        elif self._fft_window == FFTWindow.HANN:
            window_name = "hann"
        else:
            LOGGER.warning(
                f"{self.name}: Unknown window type {self._fft_window}. "
                "Defaulting to Rectangular."
            )
            window_name = "boxcar"

        # Generate the 1D window
        window_1d = get_window(window_name, self._fft_size)

        # Store the gain properties
        self._coherent_gain = np.sum(window_1d)
        self._noise_power_gain = np.sum(window_1d**2)  # This is sum-of-squares

        # Reshape to (fft_size, 1) for broadcasting against (n_samples, n_channels)
        self._window_array = window_1d.reshape(-1, 1)
        LOGGER.debug(f"{self.name}: Created {window_name} window")

    def _calculate_fft_scaling(self):
        input_media_info = self.get_input_port("in").media_info

        channels = input_media_info.dtype[1]
        n_bins = self._fft_size // 2 + 1
        
        # --- 1. Peak Scaling (for amplitude measurements) ---
        peak_scaling_factor = 2.0 / self._coherent_gain
        self._fft_scaling_peak = (
            np.ones((n_bins, channels)) * peak_scaling_factor
        )
        # Correct DC (bin 0)
        self._fft_scaling_peak[0] = 1.0 / self._coherent_gain
        # Correct Nyquist (last bin) if N is even
        if self._fft_size % 2 == 0:
            self._fft_scaling_peak[-1] = 1.0 / self._coherent_gain
            
        # --- 2. RMS Scaling (for power measurements) ---
        # This scales the peak by 1/sqrt(2)
        rms_scaling_factor = np.sqrt(2) / self._coherent_gain
        self._fft_scaling_rms = (
            np.ones((n_bins, channels)) * rms_scaling_factor
        )
        # Correct DC (bin 0)
        self._fft_scaling_rms[0] = 1.0 / self._coherent_gain
        # Note: Nyquist bin (if even) is real, not complex, 
        # so its RMS scaling is also 1.0 / coherent_gain
        if self._fft_size % 2 == 0:
            self._fft_scaling_rms[-1] = 1.0 / self._coherent_gain

    def _run(self):
        LOGGER.debug(f"{self.name}: Starting process thread")
        while self.is_running():
            with self._condition:
                # block until there are enough sampes in the buffer to calculate fft
                while len(self._buffer) < self._fft_size and self.is_running():
                    self._condition.wait()

                # check if we need to stop now
                if not self.is_running():
                    break

                # extract required data from buffer
                data = self._buffer[: self._fft_size]
                self._buffer.reduce(self._fft_size - self._fft_overlap)
                #LOGGER.debug(f"len_data: {np.shape(data)}")

            # Apply window
            windowed_data = data * self._window_array
            # Calculate fft of new data
            complex_fft = rfft(windowed_data, axis=0, n=self._fft_size)
            #LOGGER.debug(f"len_fft: {np.shape(complex_fft)}")
            abs_fft = np.abs(complex_fft)

            # Calcualte peak and power spectrum
            peak_fft = abs_fft * self._fft_scaling_peak
            rms_fft = abs_fft * self._fft_scaling_rms

            # Calcualte dB spectrum
            # Use small epsilon to avoid log10(0)
            epsilon = 1e-20 
            db_peak_fft = 20 * np.log10(peak_fft + epsilon)
            db_rms_fft = 20 * np.log10(rms_fft + epsilon)

            # Send data thru all ports
            self.send_port_data("out-abs-peak", peak_fft)
            self.send_port_data("out-db-peak", db_peak_fft)
            self.send_port_data("out-abs-rms", rms_fft)
            self.send_port_data("out-db-rms", db_rms_fft)

        LOGGER.debug(f"{self.name}: Process thread stopped")

    def on_format_received(self, port_name: str, media_info) -> None:
        super().on_format_received(port_name, media_info)
        self._create_buffer()
        self._create_window()
        self._calculate_fft_scaling()
        self._update_media_info()

    def on_input_received(self, port_name: str, data) -> None:
        super().on_input_received(port_name, data)
        if port_name == "in":
            with self._condition:
                self._buffer.extend(data)
                if len(self._buffer) >= self._fft_size:
                    self._condition.notify_all()

    def on_start(self):
        self._thread = Thread(name=f"{self.name}-worker", target=self._run)
        self._thread.start()
        return True

    def on_stop(self):
        # force process thread to wakeup
        with self._condition:
            self._condition.notify_all()

        # wait for process thread to finish
        self._thread.join()
        return True

    @property
    def fft_size(self) -> int:
        return self._fft_size

    @fft_size.setter
    def fft_size(self, fft_size: int) -> None:
        if self.is_running():
            LOGGER.error(f"{self.name}: Can't change FFT size in running state")
            return

        self._fft_size = fft_size
        
        # Recalculate scaling if format is already known
        if self.get_input_port("in").media_info:
            self._create_buffer()
            self._create_window()
            self._calculate_fft_scaling()
            self._update_media_info()

    @property
    def fft_overlap(self) -> int:
        return self._fft_overlap

    @fft_overlap.setter
    def fft_overlap(self, fft_overlap: int) -> None:
        if self.is_running():
            LOGGER.error(f"{self.name}: Can't change FFT overlapping in running state")
            return

        if fft_overlap >= self._fft_size:
            LOGGER.error(f"{self.name}: Invalid FFT overlap value")
            return

        self._fft_overlap = fft_overlap

    @property
    def fft_window(self) -> FFTWindow:
        return self._fft_window

    @fft_window.setter
    @auto_coerce_enum(FFTWindow)
    def fft_window(self, fft_window: FFTWindow) -> None:
        if self.is_running():
            LOGGER.error(f"{self.name}: Can't change FFT window in running state")
            return
        self._fft_window = fft_window
        self._create_window()  # <--- ADDED

        # Recalculate scaling if format is already known
        if self.get_input_port("in").media_info:
            self._calculate_fft_scaling()
            self._update_media_info()
