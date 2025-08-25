from .node_viewmodel import NodeViewModel
from .scope_viewmodel import ScopeViewModel

# Initialize a package-level variable
VIEWMODEL_VERSION = "1.0.0"

# Define __all__ to control wildcard imports
__all__ = ["NodeViewModel", "ScopeViewModel", "VIEWMODEL_VERSION"]
