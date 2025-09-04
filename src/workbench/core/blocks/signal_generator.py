import numpy as np
import math

from threading import Thread, Lock
from ..helpers.media_ring_buffer import MediaRingBuffer
from interval_timer import IntervalTimer
from ..media_blocks import MediaBlock
from ..media_info import MediaInfo, ChannelInfo

import logging

LOGGER = logging.getLogger(__name__)


class SignalGenerator(MediaBlock):
    def __init__(
        self,
        name,
        signal_type="sin",
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

        # Synchronization objets
        self._lock = Lock()
        self._params_changed = False

        # Ports configuration
        self.add_output_port("out")
        self._update_media_info()
        self.set_port_format("out", self._media_info)

    def _generate_sin_signal(self):
        f = self._frequency / self._samplerate
        N = math.ceil(1 / f)
        signal_length = math.ceil(self._blocksize / (10 * N)) * 10 * N

        x = np.linspace(
            0,
            2 * np.pi * f * signal_length,
            num=signal_length,
            endpoint=False,
            dtype=self._dtype,
        )
        y = self._amplitude * np.sin(x)

        self._signal = MediaRingBuffer(signal_length, dtype=self._dtype)
        self._signal.extend(y)

        self._signal_length = signal_length

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
        self._start_idx = 0
        self._end_idx = self._blocksize
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
                self._generate_sin_signal()

            # Calculate read indexes
            current_range = np.arange(self._start_idx, self._end_idx)
            wrapped_idx = np.where(current_range >= self._signal_length)
            current_range[wrapped_idx] = (
                current_range[wrapped_idx] - self._signal_length
            )

            # self.source_put(self.signal[current_range])
            self.send_port_data("out", self._signal[current_range])
            self._start_idx = (self._start_idx + self._blocksize) % self._signal_length
            self._end_idx = self._start_idx + self._blocksize

        LOGGER.debug(f"{self.name}: Producer thread Stopped")

    def on_start(self):
        self._generate_sin_signal()
        self.thread = Thread(name=f"{self.name}-worker", target=self._run)
        self.thread.start()
        return True

    def on_stop(self):
        self.thread.join()
        return True

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
