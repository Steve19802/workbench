from .audio_capture_node import AudioCaptureNode
from .scope_node import ScopeNode
from .signal_generator_node import SignalGeneratorNode
from .fft_analyzer_node import FFTAnalyzerNode
from .frequency_response_node import FrequencyResponseNode
from .curve_smoother_node import CurveSmootherNode
from .octave_smoother_node import OctaveSmootherNode
from .spectral_denoiser_node import SpectralDenoiserNode

# Initialize a package-level variable
NODES_VERSION = "1.0.0"

# Define __all__ to control wildcard imports
__all__ = ["AudioCaptureNode", 
           "ScopeNode", 
           "SignalGeneratorNode", 
           "FFTAnalyzerNode", 
           "FrequencyResponseNode",
           "CurveSmootherNode",
           "OctaveSmootherNode",
           "SpectralDenoiserNode"
           "NODES_VERSION"]
