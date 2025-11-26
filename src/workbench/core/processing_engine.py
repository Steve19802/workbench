import logging
from .base_blocks import Block
from .helpers.registry import BLOCK_REGISTRY
from enum import Enum

LOGGER = logging.getLogger(__name__)


class ProcessingEngine:
    def __init__(self) -> None:
        self._blocks = {}
        self._producers = []
        self._is_running = False

    def add_block(self, block: Block, block_id=None):
        if self._is_running:
            LOGGER.error(f"Can not add block {block_id} while the engine is running")
            return

        id = block_id if block_id is not None else block.id
        LOGGER.debug(f"Adding block with id: {id}")
        self._blocks[block_id] = block
        if block.is_producer():
            self._producers.append(block)
        block.id = id

    def remove_block(self, block_id):
        if self._is_running:
            LOGGER.error(f"Cannot remove block {block_id} while the engine is running.")
            return

        if block_id not in self._blocks:
            LOGGER.error(f"Attempted to remove non-existent block {block_id}.")
            return

        LOGGER.debug(f"Removing block {block_id}")
        block_to_remove = self._blocks.pop(block_id)

        # Disconnect ports
        for in_port in block_to_remove.get_input_ports():
            block_to_remove.get_input_port(in_port).disconnect()

        if block_to_remove.is_producer():
            # Also remove it from the list of producers
            self._producers.remove(block_to_remove)

    def clear_all_blocks(self):
        """Removes all blocks from the engine."""
        if self._is_running:
            LOGGER.error("Cannot clear blocks while engine is running.")
            return
            
        LOGGER.debug("Clearing all blocks from engine.")
        # Iterate over a copy of the keys since we're modifying the dict
        for block_id in list(self._blocks.keys()):
            self.remove_block(block_id)
            
        self._blocks.clear()
        self._producers.clear()
        
    def get_block_by_id(self, block_id: str) -> Block | None:
        """Helper to safely get a block."""
        LOGGER.debug(f"Searching for {block_id} in Blocks: {self._blocks.keys()}")
        return self._blocks.get(block_id)

    def _get_validated_ports(self, source_id, source_port, dest_id, dest_port):
        """Helper to find and validate blocks and ports. Returns (in_port, out_port) or (None, None)."""
        if source_id not in self._blocks or dest_id not in self._blocks:
            LOGGER.error("Engine: Invalid block ID provided.")
            return None, None

        out_block = self._blocks[source_id]
        in_block = self._blocks[dest_id]

        if not out_block.is_output_port_valid(source_port):
            LOGGER.error(
                f"Engine: Output port '{source_port}' not found at block '{source_id}'"
            )
            return None, None

        if not in_block.is_input_port_valid(dest_port):
            LOGGER.error(
                f"Engine: Input port '{dest_port}' not found at block '{dest_id}'"
            )
            return None, None

        return in_block.get_input_port(dest_port), out_block.get_output_port(
            source_port
        )

    def connect_ports(self, source_id, source_port, dest_id, dest_port):
        if self._is_running:
            LOGGER.error("Cannot change connections while engine is running.")
            return

        in_port, out_port = self._get_validated_ports(
            source_id, source_port, dest_id, dest_port
        )
        if in_port and out_port:
            LOGGER.debug(
                f"Engine: Connecting '{source_id}:{source_port}' to '{dest_id}:{dest_port}'"
            )
            in_port.connect(out_port)

    def disconnect_ports(self, source_id, source_port, dest_id, dest_port):
        if self._is_running:
            LOGGER.error("Cannot change connections while engine is running.")
            return

        in_port, out_port = self._get_validated_ports(
            source_id, source_port, dest_id, dest_port
        )
        if in_port and out_port:
            LOGGER.debug(
                f"Engine: Disconnecting '{source_id}:{source_port}' to '{dest_id}:{dest_port}'"
            )
            in_port.disconnect()

    def start(self):
        LOGGER.debug("Starting processing engine")
        if self._is_running:
            LOGGER.warning("Engine already runnig")
            return

        for producer in self._producers:
            producer.start()

        self._is_running = True

    def stop(self):
        LOGGER.debug("Stopping processing engine")
        if not self._is_running:
            LOGGER.warning("Engine already stopped")
            return

        for producer in self._producers:
            producer.stop()

        self._is_running = False


    def _get_block_properties(self, block) -> dict:
        """
        Returns a list of all @property names defined in a class and its ancestors.
        """
        properties = {}
        cls = block.__class__
        for base_cls in cls.__mro__:
            for name, value in base_cls.__dict__.items():
                if isinstance(value, property) and name not in properties:
                    # Check if it's a property flagges as not_serializable
                    if hasattr(value.fget, "not_serializable"):
                        continue
                    # Invoke the property getter
                    prop_value = value.__get__(block, type(block))
                    
                    # If it's an Enum we serialize it's value
                    if isinstance(prop_value, Enum):
                        prop_value = prop_value.value
                    
                    # Add propery name and value
                    properties[name] = prop_value
        return properties

    def serialize(self) -> dict:
        LOGGER.debug("Serializing processing engine state...")
        ser_obj = {}
        nodes_data = []
        connections_data = []

        for block_id, block in self._blocks.items():
            # 1. Save Block Info
            nodes_data.append({
                "id": block_id,
                "type": type(block).__name__, 
                "properties": self._get_block_properties(block)
            })
            
            # 2. Save its Input Connections
            for in_port_key in block.get_input_ports():
                in_port = block.get_input_port(in_port_key)
                source_port = in_port.get_source_port()
                if source_port:
                    source_block = source_port.get_parent_block()
                    source_block_id = source_block.id
                    
                    connections_data.append({
                        "from_node_id": source_block_id,
                        "from_port": source_port.name,
                        "to_node_id": block_id,
                        "to_port": in_port.name,
                    })

        ser_obj = {
            "nodes": nodes_data,
            "connections": connections_data
        }
        LOGGER.info(ser_obj)
        return ser_obj
    
    def deserialize(self, data: dict, blocks=True, connections=True):
        """
        Deserializes an engine state from a dictionary,
        re-creating all blocks and connections.
        
        Requires the engine to be initialized with a 'block_registry'.
        """
        if self._is_running:
            LOGGER.error("Cannot deserialize while engine is running.")
            return

        LOGGER.debug("Deserializing processing engine state...")

        nodes_data = data.get("nodes", [])
        connections_data = data.get("connections", [])

        if blocks:
            self.clear_all_blocks()
            LOGGER.debug(f"Found {len(nodes_data)} blocks")
            # --- 1. Create all block instances ---
            for node_info in nodes_data:
                block_type_str = node_info.get("type")
                block_id = node_info.get("id")
                properties = node_info.get("properties", {})

                LOGGER.debug(f"Creating block. type: {block_type_str}, id: {block_id}, properties: {properties}")
                
                if not block_type_str or not block_id:
                    LOGGER.warning("Skipping invalid node data.")
                    continue
                    
                block_class = BLOCK_REGISTRY.get(block_type_str)
                
                if block_class:
                    try:
                        # Create the block (assumes 'name' is in properties)
                        block_name = properties.get("name", block_type_str)
                        block = block_class(name=block_name)
                        LOGGER.debug(f"  block instance: {block} type: {type(block)}")
                        
                        # Set all saved properties
                        for prop, val in properties.items():
                            setattr(block, prop, val) # This uses the setter
                            
                        # Add to the engine
                        self.add_block(block, block_id)
                    except Exception as e:
                        LOGGER.error(f"Failed to create block '{block_type_str}' (ID: {block_id}): {e}")
                else:
                    LOGGER.error(f"Unknown block type '{block_type_str}'. Not found in registry.")

        if connections:
            # --- 2. Connect the blocks ---
            for conn_info in connections_data:
                self.connect_ports(
                    conn_info.get("from_node_id"),
                    conn_info.get("from_port"),
                    conn_info.get("to_node_id"),
                    conn_info.get("to_port"),
                )
            
        LOGGER.info(f"Deserialization complete. Loaded {len(self._blocks)} blocks.")
