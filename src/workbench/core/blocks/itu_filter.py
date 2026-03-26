import logging
from threading import Lock
import numpy as np

from workbench.core.base_blocks import Block
from ..helpers.itu_r_468 import ITUR468Filter
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports
from ..media_info import MediaInfo

# from ..helpers.media_ring_buffer import MediaRingBuffer

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in"], outputs=["out-filtered", "out-original"])
class ITUFilterBlock(Block):
    def __init__(self, name: str):
        super().__init__(name)
        self.filter = ITUR468Filter()
        self._samplerate = self.filter.fs
        self._numtaps = self.filter.numtaps
        self._lock = Lock()
        # self._window = 'tukey'      

    def on_format_received(self, port_name: str, media_info: MediaInfo) -> None:
        with self._lock:
            super().on_format_received(port_name, media_info)
            if media_info.samplerate != self._samplerate:
                self.filter.fs = media_info.samplerate
            out_info = media_info.copy()
            self.set_port_format("out-filtered", out_info)
            self.set_port_format("out-original", out_info)

    def on_input_received(self, port_name: str, data):
        super().on_input_received(port_name, data)
        if port_name == "in":
            # --- Your filtering logic here ---
            self.send_port_data("out-original", data)
            filtered_signal = self.filter.apply_itu_r_468_fir(data)
            self.send_port_data("out-filtered", filtered_signal)

    # def on_property_changed(self, name, value):
    #     return super().on_property_changed(name, value)

    def on_start(self):
        return True
    
    def on_stop(self):
        return True