import sounddevice as sd
import numpy as np
from ..media_info import MediaInfo, ChannelInfo
from ..media_blocks import MediaBlock
from ..helpers.not_serializable_decorator import not_serializable
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports
import logging

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(outputs=["out"])
class AudioCapture(MediaBlock):
    def __init__(
        self,
        name,
        device=None,
        channels: int = 1,
        samplerate: int = 44100,
        blocksize: int = 2048,
        calibration_factor: float = 1.0,
    ):
        super().__init__(name, samplerate, channels, blocksize)

        # Internal attributes
        self._capture_stream = None
        if device is None:
            # Get default device index
            self._device = sd.default.device[0]
        else:
            self.device = device

        device_info = sd.query_devices(self.device, "input")
        self._samplerate = samplerate or int(device_info["default_samplerate"])
        self._calibration_factor = calibration_factor
        self._media_info = None
        self._capture_stream = None

        self._capture_channels = list(range(channels))

        # Ports configuration
        #self.add_output_port("out")
    
    def init_ports(self):
        self._update_media_info()

    def _update_media_info(self):
        media_info = MediaInfo()
        media_info.name = self.name
        media_info.samplerate = self._samplerate
        media_info.dtype = (np.float64, self._channels)
        media_info.blocksize = self._blocksize
        media_info.channels = [
            ChannelInfo(name=f"Ch{i + 1}", dtype=np.float64)
            for i in range(0, self.channels)
        ]

        self._media_info = media_info
        self.set_port_format("out", self._media_info)

    def _capture_callback(self, indata, frame, time, status):
        self.send_port_data("out", self._calibration_factor * indata[:,self._capture_channels])

    def on_start(self):
        self._capture_stream = sd.InputStream(
            device=self._device,
            channels=max(self._capture_channels)+1,
            blocksize=self._blocksize,
            samplerate=self._samplerate,
            callback=self._capture_callback,
        )

        self._capture_stream.start()
        return True

    def on_stop(self):
        if self._capture_stream:
            self._capture_stream.stop()
            self._capture_stream.close()

        return True

    def on_property_changed(self, name: str, value):
        super().on_property_changed(name, value)
        self._update_media_info()

    @staticmethod
    def get_audio_devices():
        return sd.query_devices()

    @property
    @not_serializable()
    def devices(self):
        return sd.query_devices()

    @property
    def device(self) -> int | None:
        return self._device

    @device.setter
    def device(self, device):
        if self.is_running():
            LOGGER.error(f"{self.name}: Can't change capture device in running state")
            return

        new_device = -1
        if isinstance(device, str):
            device_idx = [
                i for i, dev in enumerate(sd.query_devices()) if dev["name"] == device
            ]
            if len(device_idx) > 0:
                new_device = device_idx[0]
            else:
                LOGGER.error(f"{self.name}: Input device {device} not found")
                return
        elif isinstance(device, int):
            new_device = device

        LOGGER.info(f"{self.name}: input device index is {new_device}")
        self._device = new_device
        self.on_property_changed("device", new_device)

    @property
    def calibration_factor(self) -> float:
        return self._calibration_factor

    @calibration_factor.setter
    def calibration_factor(self, factor: float):
        self._calibration_factor = float(factor)
        self.on_property_changed("calibration_factor", factor)

    @property
    def capture_channels(self):
        LOGGER.info(f"capture_channels: {self._capture_channels}")
        return self._capture_channels

    @capture_channels.setter
    def capture_channels(self, channels):
        if type(channels) == str:
            channels = [int(ch) for ch in channels.split(", ")]
            channels.sort()
        LOGGER.info(f"Capturing channels: {channels}")
        self._capture_channels = channels
        self.channels = len(channels)
