from .audio_capture import AudioCapture
from .signal_generator import SignalGenerator
from .scope_block import Scope

# Initialize a package-level variable
BLOCKS_VERSION = "1.0.0"

# Define __all__ to control wildcard imports
__all__ = ["AudioCapture", "SignalGenerator", "Scope", "BLOCKS_VERSION"]
