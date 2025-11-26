from functools import wraps
import logging

LOGGER = logging.getLogger(__name__)

def not_serializable():
    """
    Decorator for a Model's property make it not serializable.
    """
    def decorator(getter_func):
        setattr(getter_func, "not_serializable", True)
        return getter_func
    return decorator
