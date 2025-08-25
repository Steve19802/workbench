import logging
import NodeGraphQt
from NodeGraphQt.base.graph import NodeGraph
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QMessageBox,
    QWidget,
    QTableWidget,
)
from pathlib import Path

import inspect
from . import nodes
from .nodes.node_editor_view_model import NodeEditorViewModel
from ..node_factory import NodeFactory

LOGGER = logging.getLogger(__name__)
BASE_PATH = Path(__file__).parent.resolve()


class CustomNodeGraph(NodeGraph):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def delete_nodes(self, nodes, push_undo=True):
        LOGGER.debug(f"Deleting {len(nodes)} nodes")

        for node in nodes:
            if hasattr(node, "on_delete") and callable(getattr(node, "on_delete")):
                node.on_delete()

        super().delete_nodes(nodes, push_undo)


class NodeEditorWidget(QWidget):
    def __init__(self, parent=None, dock_manager=None):
        super().__init__(parent)

        self._dock_manager = dock_manager
        self._view_model = NodeEditorViewModel(dock_manager)

        self.factory = NodeFactory(dock_manager=self._dock_manager)
        # Create a node graph instance
        self.graph = CustomNodeGraph()

        # gl_widget = QOpenGLWidget()
        # self.graph.viewer().setViewport(gl_widget)

        # set up context menu for the node graph.
        hotkey_path = Path(BASE_PATH, "../resources/", "hotkeys.json")
        self.graph.set_context_menu_from_file(hotkey_path, "graph")

        # create node tree and properties bin widget.
        nodes_tree = NodeGraphQt.NodesTreeWidget(node_graph=self.graph)
        self.nodes_tree = nodes_tree

        # create the properties widget
        properties_bin = NodeGraphQt.PropertiesBinWidget(
            node_graph=self.graph, hide_control=True, disable_limit=True
        )
        self.properties_bin = properties_bin

        # --- NEW, CORRECTED WORKAROUND ---
        # Find the actual QTableWidget widget nested inside the properties bin
        table_widget = properties_bin.findChild(QTableWidget)
        if table_widget:
            # Option A: Force a one-time resize of all rows.
            # This should have a visible effect.
            table_widget.resizeRowsToContents()

            # Option B: A more robust alternative that makes resizing automatic.
            # You can try this if Option A doesn't stick.
            # vertical_header = table_widget.verticalHeader()
            # vertical_header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # --- END WORKAROUND ---

        # Register and create some default nodes for testing
        self.register_default_nodes()

        nodes_tree.update()

        # auto layout nodes
        self.graph.auto_layout_nodes()

        # Connect signals
        self.graph.node_selection_changed.connect(self.on_node_selection_changed)
        self.graph.node_created.connect(self.on_node_created)
        self.graph.nodes_deleted.connect(self._view_model.on_nodes_deleted)
        self.graph.node_double_clicked.connect(self.on_node_double_clicked)
        self._view_model.node_creation_failed.connect(self.on_node_creation_error)
        self.graph.port_connected.connect(self._view_model.on_port_connected)
        self.graph.port_disconnected.connect(self._view_model.on_port_disconnected)

    def on_node_created(self, node):
        self.properties_bin.clear_bin()
        self._view_model.on_node_created(node)
        self.properties_bin.add_node(node)

    def on_node_creation_error(self, msg, node):
        QMessageBox.critical(self, "Error Creating Node", msg)
        self.graph.delete_node(node)

    def on_nodes_deleted(self, node_ids):
        LOGGER.debug(f"Nodes deleted: {node_ids}")

    def on_node_double_clicked(self, node):
        LOGGER.debug(f"Node {node.name()} double clicked")
        if hasattr(node, "on_double_clicked") and callable(
            getattr(node, "on_double_clicked")
        ):
            node.on_double_clicked()

    def on_node_selection_changed(self, selected_nodes, unselected_nodes):
        LOGGER.debug(f"selected: {selected_nodes}, unselected: {unselected_nodes}")
        for node in unselected_nodes:
            self.properties_bin.remove_node(node)
        for node in selected_nodes:
            self.properties_bin.add_node(node)

    def on_node_connected(self, input_port, output_port):
        """
        This method is called when two nodes are connected in the GUI.
        """
        output_node = output_port.node()
        input_node = input_port.node()

        print(
            f"Connecting {output_node.name()}:{output_port.name()} to {input_node.name()}:{input_port.name()}"
        )

        # Get the backend objects from the nodes
        output_backend = output_node.get_view_model()
        input_backend = input_node.get_view_model()

        # Connect the backend objects
        input_backend.connect_input_to_output(
            input_port.name(), output_backend, output_port.name()
        )

    def on_node_disconnected(self, input_port, output_port):
        """
        This method is called when two nodes are disconnected in the GUI.
        """
        # TODO: Implement disconnection logic
        output_node = output_port.node()
        input_node = input_port.node()
        print(f"Disconnecting {output_node.name()} from {input_node.name()}")
        input_backend = input_node.get_view_model()
        input_backend.disconnect_input(input_port.name())

    def register_default_nodes(self):
        """
        Registers a couple of default node types.
        """
        # self.graph.register_node(NodeGraphQt.nodes.group_node.GroupNode)

        # Register custom nodes
        for name, obj in inspect.getmembers(nodes):
            if inspect.isclass(obj) and issubclass(obj, NodeGraphQt.BaseNode):
                LOGGER.debug(f"Found class: {name}")
                self.graph.register_node(obj)
        # self.graph.register_node(SignalGeneratorNode)
        # self.graph.register_node(MediaSourceNode)
        # self.graph.register_node(MediaProcessorNode)
        # self.graph.register_node(MediaSinkNode)
        # self.graph.register_node(AudioCaptureNode)

    @Slot()
    def start_processing(self):
        LOGGER.debug("Starting processing engine")
        self._view_model.start_engine()

    @Slot()
    def stop_processing(self):
        LOGGER.debug("Stopping processing engine")
        self._view_model.stop_engine()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    editor = NodeEditorWidget()
    editor.show()
    sys.exit(app.exec())
