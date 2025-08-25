import logging
from PySide6.QtCore import QObject, Signal


LOGGER = logging.getLogger(__name__)


class NodeViewModel(QObject):
    # A Qt signal for the View
    view_property_changed = Signal(str, object)

    def __init__(self, model):
        super().__init__()
        self.model = model

        # *** The Bridge: Connect blinker signal to a Qt slot ***
        self.model.property_changed.connect(self.on_model_property_changed)

    def get_input_ports(self):
        return self.model.get_input_ports()

    def get_output_ports(self):
        return self.model.get_output_ports()

    def get_property(self, name):
        return getattr(self.model, name, None)

    def update_property(self, name, value):
        # This logic remains the same: the View tells the ViewModel what happened.
        setattr(self.model, name, value)

    def on_model_property_changed(self, sender, **kwargs):
        """
        This is the SLOT that receives the BLINKER signal from the Model.
        'sender' is the model instance, and kwargs will contain {'name': ..., 'value': ...}.
        """
        name = kwargs.get("name")
        value = kwargs.get("value")

        LOGGER.debug(
            f"ViewModel: Received blinker signal for '{name}'. Emitting Qt signal."
        )

        # *** The Translation: Emit a QT signal for the View to hear. ***
        self.view_property_changed.emit(name, value)
