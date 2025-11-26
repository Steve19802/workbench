import logging
import shiboken6
import PySide6QtAds as Ads
from ..core.blocks import SignalGenerator, AudioCapture, Scope, FFTAnalyzer, FrequencyResponse, CurveSmoother, OctaveSmoother, SpectralDenoiser
from .viewmodels import NodeViewModel, ScopeViewModel
from .views.widgets import ScopeWidget

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")

class NodeFactory:
    def __init__(self, engine=None, dock_manager=None) -> None:
        LOGGER.debug("NodeFactory Created")
        self._engine = engine
        self._dock_manager = dock_manager
        self._dock_area = None

    def create_backend(self, identifier: str, **kwargs):
        """
        Called when the user drops a NEW node.
        Creates a FRESH Model and its ViewModel.
        """
        name = kwargs.get("name", self._get_default_name(identifier))
        id = kwargs.get("id", None)

        LOGGER.info(f"Creating model and view-model for node: identifier: \
            {identifier}, name: {name}, id: {id} ")
        
        if id is None:
            # 1. Create the fresh Backend Model
            model = self._create_model_instance(identifier, name)
        else:
            model = self._find_model_instance(id)
        
        if not model:
             raise ValueError(f"Unknown node identifier: {identifier}")

        # 2. Create the ViewModel (and side effects like Docks)
        view_model = self._create_view_model_instance(identifier, model, name)

        return model, view_model
 
    # --- Internal Helper Methods ---

    def _create_model_instance(self, identifier: str, name: str):
        """
        Pure Model creation logic.
        """
        if identifier == "AudioBlocks.SignalGeneratorNode":
            return SignalGenerator(name=name)
        elif identifier == "AudioBlocks.AudioCaptureNode":
            return AudioCapture(name=name)
        elif identifier == "AudioBlocks.ScopeNode":
            return Scope(name=name)
        elif identifier == "AudioBlocks.FFTAnalyzerNode":
            return FFTAnalyzer(name=name)
        elif identifier == "AudioBlocks.FrequencyResponseNode":
            return FrequencyResponse(name=name)
        elif identifier == "Utils.CurveSmootherNode":
            return CurveSmoother(name=name)
        elif identifier == "Utils.OctaveSmootherNode":
            return OctaveSmoother(name=name)
        elif identifier == "Utils.SpectralDenoiserNode":
            return SpectralDenoiser(name=name)

        return None

    def _find_model_instance(self, id:str):
        """
        Find a model already created
        """
        model = self._engine.get_block_by_id(id)

        return model


    def _create_view_model_instance(self, identifier: str, model, name: str):
        """
        Pure ViewModel creation logic. 
        Handles UI side-effects like Dock Widget creation.
        """
        
        # Special Case: Scope (Needs Dock Widget)
        if identifier == "AudioBlocks.ScopeNode":
            dock_widget = self._create_scope_dock(name)
            return ScopeViewModel(model, dock_widget)
            
        # Default Case: Generic NodeViewModel
        return NodeViewModel(model)

    def _create_scope_dock(self, title: str):
        """Helper to handle the complex Dock Manager logic."""
        LOGGER.debug(f"Creating scope dock widget with title: {title}")
        dock_widget = ScopeWidget(self._dock_manager, title=title)
        
        if self._dock_manager:
            if self._dock_area is None or not shiboken6.isValid(self._dock_area):
                zone = Ads.DockWidgetArea.BottomDockWidgetArea
                self._dock_manager.addDockWidget(zone, dock_widget)
            else:
                zone = Ads.DockWidgetArea.RightDockWidgetArea
                self._dock_manager.addDockWidget(zone, dock_widget, self._dock_area)
        
            self._dock_area = dock_widget.dockAreaWidget()
        
        return dock_widget

    def _get_default_name(self, identifier: str) -> str:
        """Extracts a pretty name from the identifier."""
        # e.g. "AudioBlocks.SignalGeneratorNode" -> "Signal Generator"
        parts = identifier.split('.')
        if len(parts) > 1:
            name = parts[-1].replace("Node", "")
            # Insert space before capitals (Simple regex or logic could go here)
            # For now, just return the class name part
            return name
        return "Node"
