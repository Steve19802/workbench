from blinker import Signal
import logging

LOGGER = logging.getLogger(__name__)


class Port:
    def __init__(self, name: str, owner) -> None:
        self.name = name
        self.owner = owner
        self.type = "u"

    def __repr__(self) -> str:
        return f"{self.name}.{self.type}@{self.owner.name}"


class OutputPort(Port):
    def __init__(self, name: str, owner) -> None:
        super().__init__(name, owner)
        self.type = "o"
        self._connected_port = None

        self.data_signal = Signal(f"port{id(self)}_data_signal")
        self.format_signal = Signal(f"port{id(self)}_format_signal")
        self.connect_signal = Signal(f"port{id(self)}_connect_signal")
        self.connect_signal.connect(self._on_connect)
        self.media_info = None

    def _on_connect(self, sender, **kwargs):
        # Notify owner about the connection
        connected_port = kwargs.get("connected_port")
        self.owner.on_connect(connected_port, self)
        self.update_format(self.media_info)

    def send_data(self, data) -> None:
        self.data_signal.send(self, data=data)

    def update_format(self, media_info) -> None:
        self.media_info = media_info
        self.format_signal.send(self, media_info=self.media_info)


class InputPort(Port):
    def __init__(self, name: str, owner) -> None:
        super().__init__(name, owner)
        self.type = "i"
        self._connected_port = None
        self.media_info = None

    def connect(self, output_port: OutputPort) -> None:
        if self._connected_port:
            self.disconnect()

        LOGGER.info(f"Connecting Input Port {self} to {output_port}")

        self._connected_port = output_port
        self._connected_port.data_signal.connect(self._on_data_received)
        self._connected_port.format_signal.connect(self._on_format_received)

        # Notify owner about the connection
        self.owner.on_connect(self, output_port)

        # Notify output_port that we are connected
        self._connected_port.connect_signal.send(self, connected_port=self)

    def disconnect(self) -> None:
        if self._connected_port:
            LOGGER.info(f"Disconnecting Input Port {self} from {self._connected_port}")
            self._connected_port.data_signal.disconnect(self._on_data_received)
            self._connected_port.format_signal.disconnect(self._on_format_received)
            self._connected_port = None

    def _on_data_received(self, sender, **kwargs) -> None:
        data = kwargs.get("data")
        self.owner.on_input_received(self.name, data)

    def _on_format_received(self, sender, **kwargs) -> None:
        data = kwargs.get("media_info")
        self.media_info = data
        self.owner.on_format_received(self.name, data)
