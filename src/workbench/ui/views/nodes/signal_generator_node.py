import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum

from .base_node import mirror_ports, BaseNode
from workbench.contracts.enums import SignalType
from workbench.core.blocks import SignalGenerator


LOGGER = logging.getLogger(__name__)

@mirror_ports(SignalGenerator)
class SignalGeneratorNode(BaseNode):
    """
    A node for representing an Audio Signal Generator.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Signal Generator"

    CUSTOM_PROPERTIES = {
        "signal_type": {
            "default_value": "",
            "default_items": SignalType,
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip":"Select the signal to generate",
        },
        "frequency": {
            "default_value": 1000.0,
            "range":(0, 22000.0),
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip":"Select frequency",
        },
        "amplitude": {
            "default_value": 1.0,
            "range": (0, 50.0),
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select amplitude",
        },
        "samplerate": {
            "default_value": 48000,
            "range": (0, 192000),
            "widget_type": NodePropWidgetEnum.QSPIN_BOX.value,
            "widget_tooltip": "Select input samplerate",
        },
        "blocksize": {
            "default_value": 2048,
            "range": (0, 192000),
            "widget_type": NodePropWidgetEnum.QSPIN_BOX.value,
            "widget_tooltip": "Select input block size",
        }
    }
