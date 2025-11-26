from workbench.core.blocks.spectral_denoiser import SpectralDenoiser
from .base_node import mirror_ports, BaseNode
from NodeGraphQt.constants import NodePropWidgetEnum

@mirror_ports(SpectralDenoiser)
class SpectralDenoiserNode(BaseNode):
    
    __identifier__ = "Utils"
    NODE_NAME = "Spectral Denoiser"

    CUSTOM_PROPERTIES = {
        "strength": {
            "default_value": 5,
            "range": (1, 100),
            "widget_type": NodePropWidgetEnum.QSPIN_BOX.value,
            "widget_tooltip": "Denoising strength (Window Size). Higher = Smoother.",
        }
    }
