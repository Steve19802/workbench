import logging

import NodeGraphQt

LOGGER = logging.getLogger(__name__)

LOGGER.setLevel("DEBUG")

def mirror_ports(backend_class):
    """
    Decorator for Node Views.
    Copies the port definitions from a Backend Block class.
    """
    def decorator(view_cls):
        # Read metadata from the Backend Class
        inputs = getattr(backend_class, '_meta_inputs', [])
        outputs = getattr(backend_class, '_meta_outputs', [])

        print(f"Found {len(inputs)} input ports. {inputs}")
        print(f"Found {len(outputs)} outputs ports. {outputs}")
        
        # Set the static configuration on the View Class       
        view_cls.INITIAL_INPUTS = list(inputs)
        view_cls.INITIAL_OUTPUTS = list(outputs)

        return view_cls
    return decorator

class BaseNode(NodeGraphQt.BaseNode):
    """
    A node for use in workbench.
    """

    # Unique node identifier.
    __identifier__ = "Generic"

    # Set the default node name.
    NODE_NAME = "Base Node"

    CUSTOM_PROPERTIES = {}

    INITIAL_INPUTS = [] 
    INITIAL_OUTPUTS = []

    def __init__(self):
        super(BaseNode, self).__init__()
        self._view_model = None

        self.create_property("block_id", "")
        self._initialize_custom_properties()

        self._initialize_default_ports()

    def _initialize_custom_properties(self):
        """Creates properties using defaults from the dictionary."""
        for name, config in self.CUSTOM_PROPERTIES.items():
            
            # Extract config
            default_value = config.get("default_value")
            widget_type = config.get("widget_type")
            tooltip = config.get("widget_tooltip", "")
            items = config.get("default_items", []) # Start with empty/default list
            
            # Extra args for create_property
            kwargs = {
                "widget_type": widget_type,
                "widget_tooltip": tooltip
            }
            
            # Add specific args based on type
            if "range" in config:
                kwargs["range"] = config["range"]
            if items is not None:
                kwargs["items"] = items
                
            # Create it!
            self.create_property(name, value=default_value, **kwargs)

    def _initialize_default_ports(self):
        """Creates the static ports defined in the class."""
        LOGGER.debug(f"Creating input ports: {self.INITIAL_INPUTS}")
        for name in self.INITIAL_INPUTS:
            self.add_input(name)
            
        LOGGER.debug(f"Creating output ports: {self.INITIAL_OUTPUTS}")
        for name in self.INITIAL_OUTPUTS:
            self.add_output(name)

    def _sync_properties(self):
        """
        Updates property values and item lists from the ViewModel.
        """
        self._set_property_private("block_id", self.model.id)
        for name, config in self.CUSTOM_PROPERTIES.items():
            
            # 1. Update Items (Dynamic Lists)
            # If the config has an "items_source" key, call that method on VM
            items_source_name = config.get("items_source")
            if items_source_name and hasattr(self, items_source_name):
                # Call the method on the VM (e.g., vm.get_input_devices())
                new_items = getattr(self, items_source_name)()
                
                # Update the widget
                if hasattr(self.model, 'set_items'):
                    self.model.set_items(name, new_items)
                    
                    # Update property definition internal storage if supported
                    # self.set_property_items(name, new_items) # Hypothetical API

            # 2. Update Value
            # We assume the property name in Node matches the property name in VM
            # or we can use a "model_property" key mapping.
            current_value = None
            getter = config.get("getter", None)
            if getter is not None:
                current_value = getattr(self, getter)()
            else:
                model_prop_name = config.get("model_property", name)
                current_value = self._view_model.get_property(model_prop_name)
            
            # Use your existing set_property logic (handles Enums, etc)
            # push_undo=False because this is a sync, not a user action
            self._set_property_private(name, current_value)

    def _sync_ports(self):
        """
        Ensures the View matches the Backend's ports.
        This is crucial for nodes that change ports dynamically (e.g., 'Add Channel').
        """
        if not self._view_model:
            return

        # 1. Sync Inputs
        vm_inputs = self._view_model.get_input_ports() # List of strings
        view_inputs = [p.name() for p in self.input_ports()]
        
        for name in vm_inputs:
            if name not in view_inputs:
                self.add_input(name)
                
        # 2. Sync Outputs
        vm_outputs = self._view_model.get_output_ports() # List of strings
        view_outputs = [p.name() for p in self.output_ports()]
        
        for name in vm_outputs:
            if name not in view_outputs:
                self.add_output(name)

    def _set_property_private(self, name, value, push_undo=False):
        if self.has_property(name):
            super().set_property(name, value, push_undo)

    def bind_view_model(self, view_model):
        self._view_model = view_model
        self._view_model.view_property_changed.connect(
            self.on_view_model_property_changed
        )
        self._sync_properties()
        self._sync_ports()

    def get_view_model(self):
        return self._view_model

    def set_property(self, name, value, push_undo=True):
        LOGGER.info(f"set_property: {name}, {value}")

        self._set_property_private(name, value, push_undo)
        if self._view_model:
            self._view_model.update_property(name, value)

    def on_view_model_property_changed(self, name, value):
        if self.has_property(name):
            super().set_property(name, value, push_undo=False)


