from enum import Enum


class ScopeModes(str,Enum):
    TIME = "Time"
    SPECTRUM = "Spectrum"
    XY = "XY"


class ScaleMode(str,Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
    AUTO_RANGE = "Auto Range"


class TriggerSlope(str,Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
