import logging

import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum

from .base_node import mirror_ports, BaseNode
from workbench.core.blocks.curve_smoother import CurveSmoother

LOGGER = logging.getLogger(__name__)

@mirror_ports(CurveSmoother)
class CurveSmootherNode(BaseNode):
    """
    A node for representing a CurveSmoother block.
    """

    # Unique node identifier.
    __identifier__ = "Utils"

    # Set the default node name.
    NODE_NAME = "CurveSmoother"

    CUSTOM_PROPERTIES = {
        "smoothness": {
            "range": (0.1, 500.0),
            "default_value": 1.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Set the smoothing factor",
        }
    }


