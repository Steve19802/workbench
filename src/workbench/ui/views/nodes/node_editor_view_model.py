import logging
import json
from PySide6.QtCore import QObject, Signal, QByteArray

from workbench.core.processing_engine import ProcessingEngine
from ...node_factory import NodeFactory

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")

class NodeEditorViewModel(QObject):
    engine_state_changed = Signal(bool)  # True if running, False if stopped
    node_creation_failed = Signal(str, object)

    def __init__(self, dock_manager, graph_view):
        super().__init__()
        self.engine = ProcessingEngine()
        self.factory = NodeFactory(self.engine, dock_manager)
        self.graph_view = graph_view
        self.dock_manager = dock_manager

    # --- Public methods for the UI to call ---
    def start_engine(self):
        self.engine.start()
        self.engine_state_changed.emit(True)

    def stop_engine(self):
        self.engine.stop()
        self.engine_state_changed.emit(False)

    def save_graph(self, file_path, main_window_data=None):
        """
        Orchestrates saving: merges Backend logic with Frontend layout.
        """
        LOGGER.info(f"Saving session to {file_path}")
        
        try:
            # 1. Serialize Backend (Models & Logic)
            backend_data = self.engine.serialize()
            
            # 2. Serialize Frontend (Nodes & Positions)
            frontend_data = self.graph_view.serialize_session()

            # 3. Serialize window docking manager state
            dock_manager_data = self.dock_manager.saveState().data().decode("utf-8")
            LOGGER.debug(f"dock_manager_data: {dock_manager_data}")

            

            
            # 3. Merge
            full_session_data = {
                "backend_model": backend_data,
                "frontend_view": frontend_data,
                "dock_manager": dock_manager_data,
                "main_window_data": main_window_data
            }
            
            # 4. Write to disk
            with open(file_path, 'w') as f:
                json.dump(full_session_data, f, indent=2)
                
        except Exception as e:
            LOGGER.error(f"Failed to save session: {e}")
        #dic = self.engine.serialize()
        #self.engine.deserialize(dic)
    
    def open_graph(self, file_path):
        """
        Orchestrates loading: Restores Backend first, then attaches Frontend.
        """
        LOGGER.info(f"Loading session from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # 1. Clear everything
            self.engine.clear_all_blocks()
            self.graph_view.clear_session()
            
            # 2. Restore Backend blocks only FIRST (Creates the Models)
            #    The Engine will recreate all Blocks with their original IDs.
            backend_data = data.get("backend_model", {})
            self.engine.deserialize(backend_data, connections=False)
            
            # 3. Restore Frontend SECOND (Creates the Views)
            #    NodeGraphQt will recreate nodes with their original IDs.
            frontend_data = data.get("frontend_view", {})
            self.graph_view.deserialize_session(frontend_data)

            # 4. Bind loaded blocks with their view-models and node view
            self.bind_view_models()
           
            # 5. Now that everything is binded, make the blocks interconnection
            self.engine.deserialize(backend_data, blocks=False)
           
            # 6. Restore docking window manager state
            dock_manager_data = QByteArray(data.get("dock_manager"))
            self.dock_manager.restoreState(dock_manager_data)

            LOGGER.info("Session loaded successfully.")

            return data.get("main_window_data", {})
            
        except Exception as e:
            LOGGER.error(f"Failed to load session: {e}")
            # Optional: Cleanup/Reset on failure


    def bind_view_models(self):
        LOGGER.info("Binding models and view-models")
        LOGGER.debug(f"nodes: {self.graph_view.all_nodes()}")
        for node in self.graph_view.all_nodes():
            block_id = node.get_property("block_id")
            #node.model.id = block_id
            model, view_model = self.factory.create_backend(node.type_, id=block_id, name=node.name())
            node.bind_view_model(view_model)

    # --- Slots for NodeGraphQt signals ---
    def on_node_created(self, node):
        LOGGER.info(f"Adding node '{node}' to engine")
        try:
            model, view_model = self.factory.create_backend(node.type_, name=node.name())
            self.engine.add_block(model, node.id)
            node.bind_view_model(view_model)
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
