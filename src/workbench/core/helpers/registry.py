# This will hold the mapping
BLOCK_REGISTRY = {}

def register_block(cls):
    """
    A decorator to automatically register a Block class.
    """
    # Use the class name as the identifier
    block_type = cls.__name__ 
    
    if block_type in BLOCK_REGISTRY:
        raise ValueError(f"Block type '{block_type}' is already registered!")
        
    BLOCK_REGISTRY[block_type] = cls
    return cls
