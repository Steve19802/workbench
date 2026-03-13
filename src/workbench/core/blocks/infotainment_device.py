from ..media_blocks import Block
from ..helpers.adb_device import ADBWorker
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

@register_block
@define_ports(inputs=["adb-shell-in"], outputs=["adb-shell-out"])
class InfotainmentDeviceBlock(Block):
    def __init__(self, name: str):
        super().__init__(name)
        self.adb_worker : ADBWorker = None

    def on_input_received(self, port_name: str, data):
        super().on_input_received(port_name, data)
        payload = self.adb_worker.shell(data)
        self.send_port_data("adb-shell-out", payload)
        # TODO: implement logic
        pass

    def on_start(self):
        self.adb_worker = ADBWorker()
        return self.adb_worker.start_thread()
    
    def on_stop(self):
        return self.adb_worker.close()