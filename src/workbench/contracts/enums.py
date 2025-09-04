from enum import Enum


class ScopeModes(Enum):
    TIME = "Time"
    SPECTRUM = "Spectrum"
    XY = "XY"


class ScaleMode(Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
    AUTO_RANGE = "Auto Range"


class TriggerSlope(Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
