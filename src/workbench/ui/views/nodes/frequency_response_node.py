import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum

from workbench.core.blocks.frequency_response import FrequencyResponse
from workbench.contracts.enums import FrequencyResponseMode
from .base_node import mirror_ports, BaseNode

LOGGER = logging.getLogger(__name__)

@mirror_ports(FrequencyResponse)
class FrequencyResponseNode(BaseNode):
    """
    A node for representing a FrequencyResponse block.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Frequency Response"

    CUSTOM_PROPERTIES = {
        "mode": {
            "default_value": "",
            "default_items": FrequencyResponseMode,
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip": "Select calulation mode"
        },
        "averaging_time": {
            "default_value": 5.0,
            "range": (1.0, 20.0),
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select average time window to calculate the freqcuency response",
        },
        "calibration_offset": {
            "default_value": 0.0,
            "range": (-100.0, 100.0),
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select offset to apply to the frequency response",
        }
    }


