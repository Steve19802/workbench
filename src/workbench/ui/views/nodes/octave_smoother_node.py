from workbench.core.blocks.octave_smoother import OctaveSmoother
from .base_node import mirror_ports, BaseNode
from NodeGraphQt.constants import NodePropWidgetEnum

@mirror_ports(OctaveSmoother)
class OctaveSmootherNode(BaseNode):
    
    __identifier__ = "Utils"
    NODE_NAME = "Octave Smoother"

    CUSTOM_PROPERTIES = {
        "bandwidth": {
            "default_value": 0.33, # 1/3 Octave
            "range": (0.01, 2.0),
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Smoothing bandwidth (Octaves). 0.33 is standard.",
        }
    }
