import logging
from PySide6.QtCore import QObject, Signal

from workbench.core.processing_engine import ProcessingEngine
from ...node_factory import NodeFactory

LOGGER = logging.getLogger(__name__)


class NodeEditorViewModel(QObject):
    engine_state_changed = Signal(bool)  # True if running, False if stopped
    node_creation_failed = Signal(str, object)

    def __init__(self, dock_manager):
        super().__init__()
        self.engine = ProcessingEngine()
        self.factory = NodeFactory(dock_manager)

    # --- Public methods for the UI to call ---
    def start_engine(self):
        self.engine.start()
        self.engine_state_changed.emit(True)

    def stop_engine(self):
        self.engine.stop()
        self.engine_state_changed.emit(False)

    # --- Slots for NodeGraphQt signals ---
    def on_node_created(self, node):
        LOGGER.debug(f"Adding node '{node}' to engine")
        try:
            model, view_model = self.factory.create_backend(node.type_)
            node.bind_view_model(view_model)
            self.engine.add_block(model, node.id)
        except ValueError as e:
            text = f"Failed to create node {node.name()}: {e}"
            LOGGER.error(text)
            self.node_creation_failed.emit(text, node)

    def on_port_connected(self, in_port, out_port):
        in_node = in_port.node()
        out_node = out_port.node()
        self.engine.connect_ports(
            out_node.id, out_port.name(), in_node.id, in_port.name()
        )

    def on_port_disconnected(self, in_port, out_port):
        in_node = in_port.node()
        out_node = out_port.node()
        self.engine.disconnect_ports(
            out_node.id, out_port.name(), in_node.id, in_port.name()
        )

    def on_nodes_deleted(self, node_ids):
        # This signal gives a list of IDs, perfect for the engine
        for node_id in node_ids:
            self.engine.remove_block(node_id)
