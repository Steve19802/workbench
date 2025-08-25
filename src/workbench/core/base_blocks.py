from blinker import Signal
import numpy as np
from enum import Enum
from threading import Lock
from .port import InputPort, OutputPort

import logging

LOGGER = logging.getLogger(__name__)


class Block:
    property_changed = Signal()
    data_received = Signal()
    input_format_changed = Signal()

    class BlockState(Enum):
        STOPPED = 1
        STARTED = 2

    def __init__(self, name: str) -> None:
        self.name = name
        self._input_ports = {}
        self._output_ports = {}
        self._state = Block.BlockState.STOPPED
        self._state_lock = Lock()

    def get_output_ports(self) -> list[str]:
        return list(self._output_ports.keys())

    def get_output_port(self, port_name: str) -> OutputPort | None:
        return self._output_ports.get(port_name)

    def get_input_ports(self) -> list[str]:
        return list(self._input_ports.keys())

    def get_input_port(self, port_name: str) -> InputPort | None:
        return self._input_ports.get(port_name)

    def add_input_port(self, port_name: str) -> None:
        if port_name in self._input_ports.keys():
            LOGGER.error(f"Input port {port_name} already exists")
            return

        input_port = InputPort(port_name, self)
        self._input_ports[port_name] = input_port

    def add_output_port(self, port_name: str) -> None:
        if port_name in self._output_ports.keys():
            LOGGER.error(f"Output port {port_name} already exists")
            return

        input_port = OutputPort(port_name, self)
        self._output_ports[port_name] = input_port

    def is_output_port_valid(self, port_name: str) -> bool:
        return port_name in self._output_ports.keys()

    def is_input_port_valid(self, port_name: str) -> bool:
        return port_name in self._input_ports.keys()

    def is_producer(self):
        return len(self._output_ports) > 0

    def on_property_changed(self, name: str, value):
        LOGGER.info(f"{self.name}: Property {name} changed to {value}")
        self.property_changed.send(self, name=name, value=value)

    def start(self) -> bool:
        with self._state_lock:
            if self._state == Block.BlockState.STOPPED:
                LOGGER.info(f"{self.name}: Starting...")
                self._state = Block.BlockState.STARTED
                if self.on_start():
                    return True
                else:
                    LOGGER.error(f"{self.name}: Unable to start")
                    self._state = Block.BlockState.STOPPED
                    return False
            else:
                LOGGER.info(f"{self.name}: Already started")
                return True

    def stop(self) -> bool:
        with self._state_lock:
            if self._state == Block.BlockState.STARTED:
                LOGGER.info(f"{self.name}: Stopping...")
                self._state = Block.BlockState.STOPPED
            else:
                LOGGER.info(f"{self.name}: Already stopped")
                return True

        if self.on_stop():
            return True
        else:
            with self._state_lock:
                LOGGER.error(f"{self.name}: Unable to stop")
                self._state = Block.BlockState.STARTED
                return False

    def is_running(self) -> bool:
        with self._state_lock:
            return self._state == Block.BlockState.STARTED

    def on_start(self):
        raise NotImplementedError(
            "This function must be implemented by derived classes"
        )

    def on_stop(self):
        raise NotImplementedError(
            "This function must be implemented by derived classes"
        )

    def on_connect(self, input_port, output_port) -> None:
        LOGGER.info(f"{self.name}: Port {output_port} connected to {input_port}")

    def send_port_data(self, port_name: str, data) -> None:
        if not self.is_output_port_valid(port_name):
            LOGGER.error(f"{self.name}: {port_name} is not a valid port")
            return

        LOGGER.debug(f"{self.name}: Sending {np.shape(data)} to port {port_name}")
        self._output_ports[port_name].send_data(data)

    def set_port_format(self, port_name: str, media_format) -> None:
        if not self.is_output_port_valid(port_name):
            LOGGER.error(f"{self.name}: {port_name} is not a valid port")
            return

        LOGGER.debug(
            f"{self.name}: Configuring format {media_format} to port {port_name}"
        )
        self._output_ports[port_name].update_format(media_format)

    def on_input_received(self, port_name: str, data) -> None:
        LOGGER.debug(
            f"{self.name}: data received {np.shape(data)} from port {port_name}"
        )
        self.data_received.send(self, port_name=port_name, data=data)

    def on_format_received(self, port_name: str, media_info) -> None:
        LOGGER.debug(f"{self.name}: data received {media_info} from port {port_name}")
        self.input_format_changed.send(self, port_name=port_name, media_info=media_info)
