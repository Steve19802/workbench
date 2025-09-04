import uuid
import numpy as np


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

    def channels_number(self):
        return len(self.channels)

    def __str__(self) -> str:
        return (
            f"Media Name: {self.name}, samplerate: {self.samplerate}, blocksize: {self.blocksize}, channels:\n +- "
            + "\n +- ".join(str(ch) for ch in self.channels)
        )
