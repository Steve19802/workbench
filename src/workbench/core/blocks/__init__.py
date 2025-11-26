from .audio_capture import AudioCapture
from .signal_generator import SignalGenerator
from .scope_block import Scope
from .fft_analyzer import FFTAnalyzer
from .frequency_response import FrequencyResponse
from .curve_smoother import CurveSmoother
from .octave_smoother import OctaveSmoother
from .spectral_denoiser import SpectralDenoiser

# Initialize a package-level variable
BLOCKS_VERSION = "1.0.0"

# Define __all__ to control wildcard imports
__all__ = ["AudioCapture", 
           "SignalGenerator", 
           "Scope", 
           "FFTAnalyzer", 
           "FrequencyResponse",
           "CurveSmoother",
           "OctaveSmoother",
           "SpectralDenoiser"
           "BLOCKS_VERSION"]
