from enum import Enum
import logging
import NodeGraphQt
from NodeGraphQt.base.node import NodePropWidgetEnum
from .base_node import mirror_ports, BaseNode
from workbench.core.blocks import Scope
from workbench.contracts.enums import ScopeModes, ScaleMode, TriggerSlope

LOGGER = logging.getLogger(__name__)

@mirror_ports(Scope)
class ScopeNode(BaseNode):
    """
    A node for representing a Scope / Graph node.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Scope"

    CUSTOM_PROPERTIES = {
        "mode": {
            "default_value": "",
            "default_items": ScopeModes,
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip": "Select scope mode",
        },
        "vertical_scale_mode": {
            "default_value": "",
            "default_items": ScaleMode,
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip": "Select vertical axis scale mode",
        },
        "vertical_scale_min": {
            "range": (-1000.0, 1000.0),
            "default_value": -1.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select vertical axis min value",
        },
        "vertical_scale_max": {
            "range": (-1000.0, 1000.0),
            "default_value": 1.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select vertical axis max value",
        },
        "channels_visibility": {
            "default_value": "",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT.value,
            "widget_tooltip": "Select channels visibility",
        },
        "trigger_channel": {
            "default_value": "",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT.value,
            "widget_tooltip": "Select trigger channel",
        },
        "trigger_level": {
            "range": (-1000.0, 1000.0),
            "default_value": 0.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select trigger level",
        },
        "trigger_slope": {
            "default_value": "",
            "default_items": TriggerSlope,
            "widget_type": NodePropWidgetEnum.CUSTOM_BASE.value,
            "widget_tooltip": "Select trigger slope",
        },
        "time_span": {
            "range": (0.0, 1000.0),
            "default_value": 1.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Select time span to visualize",
        },
    }

    def on_double_clicked(self):
        if self._view_model:
            self._view_model.show_window()

    def on_delete(self):
        LOGGER.debug("Deleting node")
        if self._view_model:
            self._view_model.cleanup()




class ScopeNode2(NodeGraphQt.BaseNode):
    """
    A node for representing a Scope / Graph node.
    """

    # Unique node identifier.
    __identifier__ = "AudioBlocks"

    # Set the default node name.
    NODE_NAME = "Scope"

    def __init__(self):
        super(ScopeNode, self).__init__()
        self._view_model = None

    def bind_view_model(self, view_model):
        self._view_model = view_model

        self._view_model.view_property_changed.connect(
            self.on_view_model_property_changed
        )

        for out_port_name in self._view_model.get_output_ports():
            self.add_output(out_port_name)

        for in_port_name in self._view_model.get_input_ports():
            self.add_input(in_port_name)

        # self.add_enum_property("mode2", "Mode", Scope.Modes)

        self.create_property(
            "mode",
            value=self._view_model.get_property("mode"),
            items=ScopeModes,
            widget_type=NodePropWidgetEnum.CUSTOM_BASE.value,
            widget_tooltip="Select scope mode",
        )

        self.create_property(
            "vertical_scale_mode",
            value=self._view_model.get_property("vertical_scale_mode"),
            items=ScaleMode,
            widget_type=NodePropWidgetEnum.CUSTOM_BASE.value,
            widget_tooltip="Select vertical axis scale mode",
        )

        self.create_property(
            "vertical_scale_min",
            value=self._view_model.get_property("vertical_scale_min"),
            range=(-1000.0, 1000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select vertical axis min value",
        )

        self.create_property(
            "vertical_scale_max",
            value=self._view_model.get_property("vertical_scale_max"),
            range=(-1000.0, 1000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select vertical axis max value",
        )

        self.create_property(
            "channels_visibility",
            value=self._view_model.get_property("channels_visibility"),
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="Select channels visibility",
        )

        self.create_property(
            "trigger_channel",
            value=self._view_model.get_property("trigger_channel"),
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="Select trigger channel",
        )

        self.create_property(
            "trigger_level",
            value=self._view_model.get_property("trigger_level"),
            range=(-1000.0, 1000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select trigger level",
        )

        self.create_property(
            "trigger_slope",
            value=self._view_model.get_property("trigger_slope"),
            items=TriggerSlope,
            widget_type=NodePropWidgetEnum.CUSTOM_BASE.value,
            widget_tooltip="Select trigger slope",
        )

        self.create_property(
            "time_span",
            value=self._view_model.get_property("time_span"),
            range=(0.0, 1000.0),
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select scope time span",
        )

    def get_view_model(self):
        return self._view_model

    def set_property(self, name, value, push_undo=True):
        print(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)
        if self._view_model:
            self._view_model.update_property(name, value)

    def on_view_model_property_changed(self, name, value):
        if self.has_property(name):
            super().set_property(name, value, push_undo=False)

    def on_double_clicked(self):
        if self._view_model:
            self._view_model.show_window()

    def on_delete(self):
        LOGGER.debug("Deleting node")
        if self._view_model:
            self._view_model.cleanup()
