import logging
from .base_blocks import Block

LOGGER = logging.getLogger(__name__)


class MediaBlock(Block):
    def __init__(
        self, name: str, samplerate: int, channels: int, blocksize: int
    ) -> None:
        super().__init__(name)
        self._samplerate = samplerate
        self._channels = channels
        self._blocksize = blocksize

    @property
    def samplerate(self) -> int:
        return self._samplerate

    @samplerate.setter
    def samplerate(self, samplerate: int):
        if not self.is_running():
            self._samplerate = samplerate
            self.on_property_changed("samplerate", samplerate)
        else:
            LOGGER.error(f"{self.name}: Can't change samplerate in running state")

    @property
    def channels(self) -> int:
        return self._channels

    @channels.setter
    def channels(self, channels: int):
        if not self.is_running():
            self._channels = int(channels)
            self.on_property_changed("channels", channels)
        else:
            LOGGER.error(f"{self.name}: Can't change channels in running state")

    @property
    def blocksize(self) -> int:
        return self._blocksize

    @blocksize.setter
    def blocksize(self, blocksize: int):
        if not self.is_running():
            self._blocksize = int(blocksize)
            self.on_property_changed("blocksize", blocksize)
        else:
            LOGGER.error(f"{self.name}: Can't change blocksize in running state")


class MediaSink(Block):
    def __init__(self, name: str) -> None:
        super().__init__(name)

        self.add_input_port("in")

    def on_input_received(self, port_name: str, data) -> None:
        super().on_input_received(port_name, data)

    def on_format_received(self, port_name: str, media_info) -> None:
        super().on_format_received(port_name, media_info)
