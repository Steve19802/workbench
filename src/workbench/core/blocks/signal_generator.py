import numpy as np
import math

from workbench.contracts.enums import SignalType
from threading import Thread, Lock
from ..helpers.media_ring_buffer import MediaRingBuffer
from interval_timer import IntervalTimer
from ..media_blocks import MediaBlock
from ..media_info import MediaInfo, ChannelInfo
from ..helpers.auto_coerce_enum import auto_coerce_enum
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

import logging

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(outputs=["out"])
class SignalGenerator(MediaBlock):
    def __init__(
        self,
        name,
        signal_type: SignalType = SignalType.SINE,
        amplitude: float = 1.0,
        frequency: float = 1e3,
        samplerate: int = 48000,
        channels: int = 1,
        blocksize: int = 960,
    ):
        super().__init__(name, samplerate, channels, blocksize)

        # Internal attributes
        self._frequency = frequency
        self._amplitude = amplitude
        self._signal_type = signal_type
        self._media_info = None
        self._dtype = (np.float64, channels)
        self._signal = None
        self._signal_length = 0
        self._start_idx = 0
        self._end_idx = 0

        # Synchronization objets
        self._lock = Lock()
        self._params_changed = False

        # Ports configuration
    def init_ports(self):
        self._update_media_info()
        self.set_port_format("out", self._media_info)

    def _generate_signal(self):
        """
        Master signal generation function.
        Calls the correct generator based on self._signal_type.
        """
        LOGGER.debug(f"{self.name}: Generating {self._signal_type.value} signal")
        
        if self._signal_type == SignalType.SINE:
            self._generate_sine()
        elif self._signal_type == SignalType.PINK_NOISE:
            self._generate_pink_noise()    
        elif self._signal_type == SignalType.MULTI_TONE:
            self._generate_multitone()
        else:
            LOGGER.error(f"{self.name}: Unknown signal type {self._signal_type}")
            # Generate silence as a fallback
            self._signal_length = self._blocksize * 10
            silence = np.zeros((self._signal_length, self._channels))
            self._signal = MediaRingBuffer(self._signal_length, dtype=self._dtype)
            self._signal.extend(silence)
        
        # Reset read indices
        self._start_idx = 0
        self._end_idx = self._blocksize

    def _generate_sine(self):
        f = self._frequency / self._samplerate
        
        if f == 0:
            N = self._samplerate # 1 second buffer
        else:
            N = math.ceil(1 / f)
        
        signal_length = math.ceil(self._blocksize / (10 * N)) * 10 * N

        x = np.linspace(
            0,
            2 * np.pi * f * signal_length,
            num=signal_length,
            endpoint=False,
            dtype=np.float64,
        )
        y_1d = self._amplitude * np.sin(x)

        # Tile 1D signal across all channels
        y = np.tile(y_1d.reshape(-1, 1), (1, self._channels))
        
        self._signal = MediaRingBuffer(signal_length, dtype=self._dtype)
        self._signal.extend(y)

        self._signal_length = signal_length

    def _generate_pink_noise(self):
        """
        Generates a long, looping buffer of pink noise.
        Uses the FFT-filter method (1/sqrt(f)).
        """
        # Create a 5-second buffer
        signal_length = self._samplerate * 5
        
        # 1. Generate white noise for all channels
        white_noise = np.random.normal(
            0, 1, (signal_length, self._channels)
        )
        
        # 2. FFT
        white_fft = np.fft.rfft(white_noise, axis=0)
        
        # 3. Create 1/sqrt(f) filter
        n_bins = white_fft.shape[0]
        freqs = np.fft.rfftfreq(signal_length, d=1/self._samplerate)[:n_bins]
        freqs[0] = 1e-20  # Avoid divide-by-zero at DC
        
        # Amplitude filter is 1/sqrt(f)
        pink_filter = 1.0 / np.sqrt(freqs)
        pink_filter[0] = 1.0 # Don't scale DC
        
        # Reshape filter to (n_bins, 1) to broadcast across channels
        pink_filter = pink_filter.reshape(-1, 1)

        # 4. Apply filter
        pink_fft = white_fft * pink_filter
        
        # 5. IFFT
        pink_noise = np.fft.irfft(pink_fft, axis=0)
        
        # 6. Normalize to [-1, 1] and apply amplitude (Peak scaling)
        max_abs = np.max(np.abs(pink_noise), axis=0)
        pink_noise /= (max_abs + 1e-20) # Avoid zero-division
        pink_noise *= self._amplitude
        
        # 7. Store in ring buffer
        self._signal = MediaRingBuffer(signal_length, dtype=self._dtype)
        self._signal.extend(pink_noise)
        self._signal_length = signal_length

    def _generate_multitone(self):
        """
        Generates a Log-Spaced Multi-Tone signal (1/3 Octave spacing).
        Uses Newman Phases to minimize Crest Factor.
        """
        # 1. Define ISO 1/3 Octave Centers (approximate)
        #    From 20 Hz to 20 kHz
        f_min = 20.0
        f_max = 20000.0
        if f_max > self._samplerate / 2:
            f_max = self._samplerate / 2 * 0.9
            
        # Generate log-spaced frequencies
        # 3 bands per octave
        bands_per_oct = 3
        n_octaves = np.log2(f_max / f_min)
        n_tones = int(n_octaves * bands_per_oct) + 1
        
        freqs = f_min * (2 ** (np.arange(n_tones) / bands_per_oct))
        
        # 2. Generate Signal
        #    We need a buffer long enough to hold the lowest frequency cycle
        #    But for a loop, standard blocksize might be too short.
        #    Let's generate 1 second to be safe/simple.
        duration = 1.0
        N = int(self._samplerate * duration)
        t = np.arange(N) / self._samplerate
        t = t.reshape(-1, 1) # Broadcast for channels
        
        total_signal = np.zeros((N, self._channels))
        
        # 3. Sum Sines with Newman Phases
        #    Phi_k = (pi * k^2) / Num_Tones
        k_indices = np.arange(len(freqs))
        phases = (np.pi * (k_indices**2)) / len(freqs)
        
        # We iterate to save memory (creating a huge matrix can crash)
        for i, f in enumerate(freqs):
            # Amplitude correction:
            # If we sum 30 tones, amplitude is high. We scale by 1/sqrt(N_tones)
            # to keep RMS reasonable, roughly.
            amp = self._amplitude / np.sqrt(len(freqs))
            
            tone = amp * np.sin(2 * np.pi * f * t + phases[i])
            total_signal += tone

        # 4. Store
        self._signal = MediaRingBuffer(N, dtype=self._dtype)
        self._signal.extend(total_signal)
        self._signal_length = N

    def _update_media_info(self):
        media_info = MediaInfo()
        media_info.name = self.name
        media_info.samplerate = self._samplerate
        media_info.dtype = (np.float64, self._channels)
        media_info.blocksize = self._blocksize
        media_info.channels = [
            ChannelInfo(name=f"Ch{i}", dtype=np.float64)
            for i in range(0, self._channels)
        ]
        self._media_info = media_info

    def _run(self):
        LOGGER.debug(f"{self.name}: Starting producer thread")
        #self._start_idx = 0
        #self._end_idx = self._blocksize
        block_time = self._blocksize / self._samplerate
        for interval in IntervalTimer(block_time):
            if not self.is_running():
                break

            needs_update = False
            with self._lock:
                if self._params_changed:
                    needs_update = True
                    self._params_changed = False

            if needs_update:
                LOGGER.debug(f"{self.name}: Generating signal")
                self._generate_signal()

            # Calculate read indexes
            current_range = np.arange(self._start_idx, self._end_idx)
            #wrapped_idx = np.where(current_range >= self._signal_length)
            #current_range[wrapped_idx] = (
            #    current_range[wrapped_idx] - self._signal_length
            #)
            current_range = np.mod(current_range, self._signal_length)

            # self.source_put(self.signal[current_range])
            self.send_port_data("out", self._signal[current_range])
            #self._start_idx = (self._start_idx + self._blocksize) % self._signal_length
            self._start_idx = np.mod(self._start_idx + self._blocksize, self._signal_length)
            self._end_idx = self._start_idx + self._blocksize

        LOGGER.debug(f"{self.name}: Producer thread Stopped")

    def on_start(self):
        self._generate_signal()
        self.thread = Thread(name=f"{self.name}-worker", target=self._run)
        self.thread.start()
        return True

    def on_stop(self):
        self.thread.join()
        return True

    @property
    def signal_type(self) -> SignalType:
        return self._signal_type

    @signal_type.setter
    @auto_coerce_enum(SignalType)
    def signal_type(self, sig_type: SignalType):
        with self._lock:
            if self._signal_type != sig_type:
                LOGGER.debug(f"{self.name}: Changing signal type to {sig_type.value}")
                self._signal_type = sig_type
                self._params_changed = True
                self.on_property_changed("signal_type", sig_type)

    @property
    def frequency(self) -> float:
        return self._frequency

    @frequency.setter
    def frequency(self, frequency: float):
        with self._lock:
            if self._frequency != frequency:
                LOGGER.debug(f"{self.name}: Changing frequency to {frequency}")
                self._frequency = frequency
                self._params_changed = True
                self.on_property_changed("frequency", frequency)

    @property
    def amplitude(self) -> float:
        return self._amplitude

    @amplitude.setter
    def amplitude(self, amplitude: float):
        with self._lock:
            if self._amplitude != amplitude:
                self._amplitude = amplitude
                self._params_changed = True
                self.on_property_changed("amplitude", amplitude)
