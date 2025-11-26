from enum import Enum
from functools import wraps
import logging

LOGGER = logging.getLogger(__name__)

def auto_coerce_enum(enum_class: type[Enum]):
    """
    Decorator for a Model's property setter that auto-converts a
    string value (from deserialization) into the correct Enum member.
    """
    def decorator(setter_func):
        @wraps(setter_func)
        def wrapper(model_instance, value):
            # Check if the incoming value is a string
            if isinstance(value, str):
                try:
                    # Convert it to the Enum
                    value = enum_class(value)
                except ValueError:
                    LOGGER.error(f"Invalid enum value '{value}' for {enum_class.__name__}")
                    # Fallback to the first member
                    value = list(enum_class)[0]
            
            # Call the original setter with the (now-guaranteed) Enum object
            return setter_func(model_instance, value)
        return wrapper
    return decorator
