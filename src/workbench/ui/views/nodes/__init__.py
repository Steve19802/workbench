from .audio_capture_node import AudioCaptureNode
from .scope_node import ScopeNode
from .signal_generator_node import SignalGeneratorNode

# Initialize a package-level variable
NODES_VERSION = "1.0.0"

# Define __all__ to control wildcard imports
__all__ = ["AudioCaptureNode", "ScopeNode", "SignalGeneratorNode", "NODES_VERSION"]
