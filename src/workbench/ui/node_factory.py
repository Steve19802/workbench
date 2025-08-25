import logging
import shiboken6
import PySide6QtAds as Ads
from ..core.blocks import SignalGenerator, AudioCapture, Scope
from .viewmodels import NodeViewModel, ScopeViewModel
from .views.widgets import ScopeWidget

LOGGER = logging.getLogger(__name__)


class NodeFactory:
    def __init__(self, dock_manager=None) -> None:
        LOGGER.debug("NodeFactory Created")
        self._dock_manager = dock_manager
        self._dock_area = None

    def create_backend(self, identifier: str, **kwargs):
        """
        Creates and returns the Model and ViewModel for a given node identifier.
        """
        model = None
        view_model = None

        if (
            identifier == "AudioBlocks.SignalGeneratorNode"
        ):  # Match the node's __identifier__
            model = SignalGenerator(name=kwargs.get("name", "Signal Generator"))
            view_model = NodeViewModel(model)

        elif identifier == "AudioBlocks.AudioCaptureNode":
            model = AudioCapture(name=kwargs.get("name", "Audio Capture"))
            view_model = NodeViewModel(model)

        elif identifier == "AudioBlocks.ScopeNode":
            name = kwargs.get("name", "Scope Sink")
            model = Scope(name=name)
            dock_widget = ScopeWidget(self._dock_manager, title=name)
            if self._dock_manager:
                if self._dock_area is None or not shiboken6.isValid(self._dock_area):
                    zone = Ads.DockWidgetArea.BottomDockWidgetArea
                    self._dock_manager.addDockWidget(zone, dock_widget)
                    self._dock_area = dock_widget.dockAreaWidget()
                else:
                    zone = Ads.DockWidgetArea.CenterDockWidgetArea
                    self._dock_manager.addDockWidget(zone, dock_widget, self._dock_area)

            view_model = ScopeViewModel(model, dock_widget)

        # ... elif for other node types ...

        if not view_model:
            raise ValueError(f"Unknown node identifier: {identifier}")

        return model, view_model
