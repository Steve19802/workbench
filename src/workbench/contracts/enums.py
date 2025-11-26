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

class FFTWindow(str,Enum):
    RECTANGULAR = "Rectangular"
    BLACKMAN_HARRIS = "Blackman-Harris"
    FLAT_TOP = "Flat-Top"
    HANN = "Hanning"

class FrequencyResponseMode(str,Enum):
    NONE = "None"
    PINK_NOISE = "Pink Noise"
    MULTI_TONE = "Multi-tone"

class SignalType(str,Enum):
    """Defines the available signal types for the generator."""
    SINE = "Sine"
    PINK_NOISE = "Pink Noise"
    MULTI_TONE = "Multi-tone"
