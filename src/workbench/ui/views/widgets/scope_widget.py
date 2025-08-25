import logging
from ...viewmodels import ScopeViewModel
from .graph_controller_widget import GraphControllerWidget
from PySide6QtAds import CDockManager, CDockWidget


LOGGER = logging.getLogger(__name__)


class ScopeWidget(CDockWidget):
    def __init__(self, dock_manager: CDockManager, title: str) -> None:
        super().__init__(dock_manager, title)
        self._view_model: ScopeViewModel | None = None

        self._graph_controller = GraphControllerWidget()
        self.setWidget(self._graph_controller)
        self.setToolBar(self._graph_controller.get_toolbar())
        self._graph_controller.setMinimumSize(400, 200)

        self.setFeature(CDockWidget.DockWidgetFeature.DeleteContentOnClose, True)

    def bind_view_model(self, view_model: ScopeViewModel):
        self._view_model = view_model
        self._graph_controller.bind_view_model(view_model)
