from enum import Enum
import numpy as np
from scipy.fft import rfft

from threading import Condition, Thread, Lock
from ..media_blocks import Block
from ..media_info import MediaInfo, ChannelInfo
from ..helpers.media_ring_buffer import MediaRingBuffer

import logging

LOGGER = logging.getLogger(__name__)


class FFTWindow(Enum):
    RECTANGULAR = 1


class FFTAnalyzer(Block):
    def __init__(
        self,
        name: str,
        fft_size: int = 4096,
        fft_window=FFTWindow.RECTANGULAR,
        fft_overlap: int = 0,
    ) -> None:
        super().__init__(name)

        # Internal attributes
        self._fft_size = fft_size
        self._fft_overlap = fft_overlap
        self._fft_window = fft_window
        self._fft_scaling = 1.0
        self._buffer = None
        self._condition = Condition()

        # Synchronization objects
        self._lock = Lock()

        # Port configuration
        self.add_input_port("in")
        self.add_output_port("out-abs")
        self.add_output_port("out-db")

    def _update_media_info(self):
        input_media_info = self.get_input_port("in").media_info
        output_media_info = MediaInfo()
        output_media_info.name = self.name
        output_media_info.sample_rate = input_media_info.sample_rate / self._fft_size
        output_media_info.dtype = (np.float64, input_media_info.channels_number)
        output_media_info.blocksize = self._fft_size // 2 + 1
        output_media_info.channels = [
            ChannelInfo(name=f"X[{ch.name}]", dtype=np.float64)
            for ch in input_media_info.channels
        ]
        self.set_port_format("out-abs", output_media_info)
        self.set_port_format("out-db", output_media_info)

    def _create_buffer(self):
        input_media_info = self.get_input_port("in").media_info
        in_blocksize = input_media_info.blocksize
        buffer_size = 2 * (self._fft_size + in_blocksize)
        self._buffer = MediaRingBuffer(buffer_size, input_media_info.dtype, False)

    def _calculate_fft_scaling(self):
        input_media_info = self.get_input_port("in").media_info
        channels = input_media_info.dtype[1]
        self._fft_scaling = (
            np.ones((int(self._fft_size / 2) + 1, channels))
            * np.sqrt(2)
            / self._fft_size
        )
        self._fft_scaling[0] = 1 / self._fft_size

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

            # Calculate fft of new data
            complex_fft = rfft(data, axis=0, n=self._fft_size)
            abs_fft = np.abs(complex_fft) * self._fft_scaling

            self.send_port_data("out-abs", abs_fft)

            db_fft = 20 * np.log10(abs_fft)

            self.send_port_data("out-db", db_fft)

        LOGGER.debug(f"{self.name}: Process thread stopped")

    def on_format_received(self, port_name: str, media_info) -> None:
        super().on_format_received(port_name, media_info)
        self._create_buffer()
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
    def fft_window(self, fft_window: FFTWindow) -> None:
        if self.is_running():
            LOGGER.error(f"{self.name}: Can't change FFT window in running state")
            return
        self._fft_window = fft_window
