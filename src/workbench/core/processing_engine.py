import logging
from .base_blocks import Block

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

        if block_to_remove.is_producer():
            # Also remove it from the list of producers
            self._producers.remove(block_to_remove)

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
