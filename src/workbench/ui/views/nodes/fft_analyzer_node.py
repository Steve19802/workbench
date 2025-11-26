import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum
from .base_node import mirror_ports, BaseNode
from workbench.core.blocks.fft_analyzer import FFTAnalyzer
from workbench.contracts.enums import FFTWindow

LOGGER = logging.getLogger(__name__)

@mirror_ports(FFTAnalyzer)
class FFTAnalyzerNode(BaseNode):
    """
    A node for representing a FFTAnalyzer.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "FFT Analyzer"

    CUSTOM_PROPERTIES = {
        "fft_size": {
            "range": (2048, 48000),
            "default_value": 4096,
            "widget_type": NodePropWidgetEnum.QSPIN_BOX.value,
            "widget_tooltip": "Select FFT size"
        },
        "fft_window": {
            "default_items": FFTWindow,
            "default_value": "",
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip": "Select scope mode",
        },
        "fft_overlap": {
            "range": (0, 48000),
            "default_value": 0,
            "widget_type": NodePropWidgetEnum.QSPIN_BOX.value,
            "widget_tooltip": "Select FFT block overlap in samples"
        }
    }

