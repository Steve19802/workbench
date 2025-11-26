from __future__ import annotations
import uuid
import numpy as np
from typing import ClassVar

class ChannelInfo:
    def __init__(self, name=None, dtype=np.float64, unit=None) -> None:
        if name is None:
            self.name = f"ch-{uuid.uuid4()}"
        else:
            self.name = name
        self.dtype = dtype
        self.unit = unit

    def __str__(self) -> str:
        return f"Channel {self.name}, dtype: {str(self.dtype)}, unit: {self.unit}"


class MediaInfo:
    def __init__(self) -> None:
        self.name = f"media-{uuid.uuid4()}"
        self.samplerate = np.nan
        self.channels = []
        self.dtype = (np.float64, 1)
        self.blocksize = np.nan
        self.metadata = {}

    def channels_number(self):
        return len(self.channels)

    def copy(self) -> ClassVar["MediaInfo"]:
        cpy = MediaInfo()
        cpy.name = self.name
        cpy.samplerate = self.samplerate
        cpy.dtype = self.dtype
        cpy.blocksize = self.blocksize
        cpy.metadata = self.metadata.copy()
        
        for ch in self.channels:
            cpy.channels.append(ChannelInfo(ch.name, ch.dtype, ch.unit))

        return cpy

    def __str__(self) -> str: 
        metadata_str = (
            str(self.metadata) if self.metadata else "None"
        )
        return (
            f"Media Name: {self.name}, samplerate: {self.samplerate}, blocksize: {self.blocksize}, metadata: {metadata_str}, channels:\n +- "
            + "\n +- ".join(str(ch) for ch in self.channels)
        )
