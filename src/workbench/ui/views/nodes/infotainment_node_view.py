from NodeGraphQt import BaseNode

class InfotainmentNode(BaseNode):
    __identifier__ = 'Mirgor'
    NODE_NAME = 'Infotainment device'

    def __init__(self):
        super().__init__()
        self._view_model = None
        self.add_input('adb-shell-in')
        self.add_output('adb-shell-out')

    def bind_view_model(self, view_model):
        self._view_model = view_model
        # Create UI properties from the model's properties
        
    
    def set_property(self, name, value):
        super().set_property(name, value)
        # Push property changes from the UI to the model
        # setattr(self._view_model.model, name, value)