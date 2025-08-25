import logging
import NodeGraphQt

LOGGER = logging.getLogger(__name__)


class ScopeNode(NodeGraphQt.BaseNode):
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

    def get_view_model(self):
        return self._view_model

    def set_property(self, name, value, push_undo=True):
        print(f"set_property: {name}, {value}")

        super().set_property(name, value, push_undo)

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
