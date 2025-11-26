import functools

def define_ports(inputs: list[str] = None, outputs: list[str] = None):
    """
    Decorator for Backend Blocks.
    1. Stores port config as metadata on the Class.
    2. Automatically creates ports in __init__.
    """
    def decorator(cls):
        # 1. Store Metadata on the Class (Static)
        # We use specific attribute names to avoid collisions
        cls._meta_inputs = inputs or []
        cls._meta_outputs = outputs or []

        # 2. Patch __init__ to create ports automatically (Runtime)
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            
            # Auto-create the ports defined in the decorator
            for port_name in cls._meta_inputs:
                # Avoid duplicates if __init__ manually added it
                if not self.get_input_port(port_name):
                    self.add_input_port(port_name)
                    
            for port_name in cls._meta_outputs:
                if not self.get_output_port(port_name):
                    self.add_output_port(port_name)

            self.init_ports()

        cls.__init__ = new_init
        return cls
        
    return decorator
