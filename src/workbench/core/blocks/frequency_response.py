import numpy as np

from collections import deque
from scipy.interpolate import interp1d

from workbench.contracts.enums import ScopeModes, TriggerSlope
from workbench.contracts.enums import FrequencyResponseMode
from ..media_blocks import Block
from ..media_info import MediaInfo, ChannelInfo
from ..helpers.media_ring_buffer import MediaRingBuffer
from ..helpers.auto_coerce_enum import auto_coerce_enum
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

import logging

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in-abs-rms"], outputs=["freq-resp"])
class FrequencyResponse(Block):
    def __init__(
        self,
        name: str,
        mode: FrequencyResponseMode = FrequencyResponseMode.PINK_NOISE,
        averaging_time: float = 2.0,
    ) -> None:
        super().__init__(name)

        # Internal attributes
        self._mode = mode
        self._averaging_time = max(0.1, averaging_time)
        self._calibration_offset_db = 0.0
        
        # Internal state for averaging
        self._power_sum = None
        self._frame_buffer = deque()
        self._target_frame_count = 1

        # Internal state for correction
        self._correction_curve_db = 0.0
        
        # Stored properties from format
        self._n_bins = 0
        self._n_channels = 0
        

    def _update_media_info(self):
        input_media_info = self.get_input_port("in-abs-rms").media_info

        # --- Setup the output format ---
        out_info = input_media_info.copy()
        out_info.name = self.name

        # Clear the FFT metadata as it's no longer just an FFT
        out_info.metadata = {
            'domain': 'frequency',
            'analysis_mode': self._mode.value,
            'averaging_time_s': self._averaging_time,
            'fft_size': input_media_info.metadata['fft_size'],
            'audio_samplerate': input_media_info.metadata['audio_samplerate']
        }
        self.set_port_format("freq-resp", out_info)

        # --- Must be in this order ---
        # 1. Create correction curve (needs metadata)
        self._create_correction_curve(input_media_info) 
        
        # 2. Allocate buffer (and reset)
        self.reset_average() 

    def on_format_received(self, port_name: str, media_info) -> None:
        super().on_format_received(port_name, media_info)
        
        # Store dimensions
        self._n_bins = media_info.blocksize
        self._n_channels = media_info.channels_number()
        
        # Calculate target frame count for averaging
        fft_frame_rate = media_info.samplerate
        self._target_frame_count = max(
            1, int(self._averaging_time * fft_frame_rate)
        )
        LOGGER.debug(f"{self.name}: Averaging over {self._target_frame_count} frames.")

        self._update_media_info()

        
    def _create_correction_curve(self, media_info: MediaInfo):
        """Helper to build the pink noise correction curve."""
        
        # Reset to no correction
        self._correction_curve_db = 0.0
        
        if self._mode == FrequencyResponseMode.PINK_NOISE:
            LOGGER.debug(f"{self.name}: Creating Pink Noise correction curve.")
            
            # --- CRITICAL: Read metadata from FFTAnalyzer ---
            if 'fft_size' not in media_info.metadata or \
               'audio_samplerate' not in media_info.metadata:
                
                LOGGER.error(f"{self.name}: Input MediaInfo is missing critical "
                             "'fft_size' or 'audio_samplerate' metadata. "
                             "Cannot create pink noise correction.")
                LOGGER.error("Please update your FFTAnalyzer to add "
                             "'audio_samplerate' = input_media_info.samplerate "
                             "to its output metadata.")
                return

            fft_size = media_info.metadata['fft_size']
            audio_sr = media_info.metadata['audio_samplerate']
            
            # --- Calculate +3dB/octave (+10dB/decade) curve ---
            
            # 1. Get frequency axis
            freq_axis = np.fft.rfftfreq(fft_size, d=1.0 / audio_sr)
            
            # 2. Avoid log(0) for DC bin
            freq_axis[0] = 1e-20
            
            # 3. Calculate correction, normalized to 0dB at 1kHz
            f_ref = 1000.0 
            correction_db = 10 * np.log10(freq_axis / f_ref)
            
            # Reshape for broadcasting against (n_bins, n_channels)
            self._correction_curve_db = correction_db.reshape(-1, 1)
 
    def on_input_received(self, port_name: str, data) -> None:
        """Process one frame of absolute FFT data."""
        
        super().on_input_received(port_name, data)
        if port_name == "in-abs-rms":
            if self._mode == FrequencyResponseMode.PINK_NOISE:
                self._process_pink_noise(data)
            elif self._mode == FrequencyResponseMode.MULTI_TONE:
                self._process_multitone(data)

    def _process_pink_noise(self, data):
        # data is 'abs-rms', so data^2 is 'power'
        new_power_frame = data**2
        
        # --- MOVING AVERAGE LOGIC ---
        
        # 1. Add new frame to buffer and sum
        self._frame_buffer.append(new_power_frame)
        self._power_sum += new_power_frame

        # 2. If buffer is full, subtract the oldest frame
        if len(self._frame_buffer) > self._target_frame_count:
            old_power_frame = self._frame_buffer.popleft()
            self._power_sum -= old_power_frame

        # 3. Get current state for calculation
        current_sum = self._power_sum
        current_count = len(self._frame_buffer)

        if current_count == 0:
            return

        # Calculate the mean-square (average power)
        mean_square = current_sum / current_count
        
        # Convert back to RMS
        rms_spectrum_linear = np.sqrt(mean_square)

        # 2. Convert to dB
        epsilon = 1e-20 # Avoid log10(0)
        rms_spectrum_db = 20 * np.log10(rms_spectrum_linear + epsilon)

        # 3. Apply Correction (dB Domain)
        final_spectrum_db = rms_spectrum_db + self._correction_curve_db

        # 4. Send Data
        self.send_port_data('freq-resp', final_spectrum_db)

    def _process_multitone(self, data):
        """
        Analyzes specific log-spaced bins and interpolates.
        data input: Expecting 'out-db-peak' or 'out-abs-peak' from FFTAnalyzer.
        """
        # We need the linear frequency axis to map tones to bins
        # (You should cache this in on_format_received)
        if self._n_bins == 0: return
        
        # 1. Re-calculate the Target Frequencies (Same as Generator)
        #    (Ideally, calculate this ONCE in on_format_received)
        f_min = 20.0
        f_max = 20000.0
        audio_sr = 48000 # Get this from metadata!
        
        bands_per_oct = 3
        n_octaves = np.log2(f_max / f_min)
        n_tones = int(n_octaves * bands_per_oct) + 1
        target_freqs = f_min * (2 ** (np.arange(n_tones) / bands_per_oct))
        
        # 2. Map Frequencies to FFT Bin Indices
        #    bin = f * FFT_Size / SR
        fft_size = (self._n_bins - 1) * 2
        bin_indices = np.round(target_freqs * fft_size / audio_sr).astype(int)
        
        # Clamp to valid range
        bin_indices = np.clip(bin_indices, 1, self._n_bins - 1)
        
        # 3. Extract Amplitudes
        #    We want to extract the values at these indices.
        #    data shape: (n_bins, n_channels)
        
        n_channels = data.shape[1]
        output_spectrum = np.zeros_like(data)
        
        # Full linear axis for interpolation (0 Hz to Nyquist)
        full_freq_axis = np.linspace(0, audio_sr/2, self._n_bins)
        
        for ch in range(n_channels):
            # Extract values at the tone bins
            measured_points = data[bin_indices, ch]
            
            # 4. Interpolate
            #    We connect the dots between our measured tones.
            #    'linear' interpolation looks best for Bode plots (straight lines on log scale)
            #    fill_value="extrapolate" handles the edges ( < 20Hz and > 20kHz)
            
            interpolator = interp1d(
                target_freqs, 
                measured_points, 
                kind='linear', 
                bounds_error=False, 
                fill_value=(measured_points[0], measured_points[-1])
            )
            
            # Generate the full resolution curve
            output_spectrum[:, ch] = interpolator(full_freq_axis)
            
        # 5. Apply Calibration
        output_spectrum += self._calibration_offset_db
        
        self.send_port_data('freq-resp', output_spectrum)

    def on_start(self):
        self.reset_average()
        return True

    def on_stop(self):
        return True

    def reset_average(self):
        """Public method to manually restart the averaging."""
        self._frame_buffer.clear()
        
        # Initialize (or reset) the sum
        if self._n_bins > 0 and self._n_channels > 0:
            self._power_sum = np.zeros((self._n_bins, self._n_channels))
            LOGGER.debug(f"{self.name}: Averager reset.")
        else:
            self._power_sum = None # Not yet initialized

# --- Properties ---

    @property
    def mode(self) -> FrequencyResponseMode:
        return self._mode
    
    @mode.setter
    @auto_coerce_enum(FrequencyResponseMode)
    def mode(self, new_mode: FrequencyResponseMode):
        if self._mode == new_mode:
            return
        
        self._mode = new_mode
        LOGGER.info(f"{self.name}: Mode changed to {new_mode.value}.")
        
        # Re-calculate correction if format is already known
        in_port = self.get_input_port("in-abs")
        if in_port and in_port.media_info:
            self._create_correction_curve(in_port.media_info)

    @property
    def averaging_time(self) -> float:
        return self._averaging_time
    
    @averaging_time.setter
    def averaging_time(self, new_time_s: float):
        new_time_s = max(0.1, new_time_s) # Enforce min
        if self._averaging_time == new_time_s:
            return
            
        self._averaging_time = new_time_s
        
        # Re-calculate target frame count if format is already known
        in_port = self.get_input_port("in-abs")
        if in_port and in_port.media_info:
            fft_frame_rate = in_port.media_info.samplerate
            self._target_frame_count = max(
                1, int(self._averaging_time * fft_frame_rate)
            )
        LOGGER.info(f"{self.name}: Averaging time set to {new_time_s}s.")
   
    @property
    def calibration_offset(self) -> float:
        return self._calibration_offset_db

    @calibration_offset.setter
    def calibration_offset(self, new_value:float):
        self._calibration_offset_db = new_value
