from functools import partial
import logging
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QLabel, QWidget
import PySide6QtAds as QtAds

from .custom_title_bar import CustomTitleBar

LOGGER = logging.getLogger(__name__)


class CustomDockManager(QtAds.CDockManager):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # IMPORTANT: if you don't reset the default stylesheet the global stylesheet
        # won't be applied
        self.setStyleSheet("")

        self.floatingWidgetCreated.connect(self._on_floating_widget_created)

    def _on_floating_widget_created2(self, floating_widget):
        LOGGER.debug("floating window created")
        floating_widget.setTitleBarWidget(QWidget())
        floating_widget.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        floating_widget.setParent(None)
        floating_widget.setStyleSheet(self.styleSheet())

    def _on_floating_widget_created(self, floating_widget):
        LOGGER.debug("floating window created")
        floating_widget.setTitleBarWidget(CustomTitleBar(floating_widget))
        floating_widget.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.FramelessWindowHint
        )
        floating_widget.setMouseTracking(True)
        floating_widget.setParent(None)
        floating_widget.setStyleSheet(self.styleSheet())

    def addDockWidget(self, area, widget, area_widget=None, index=-1):
        widget.topLevelChanged.connect(partial(self._on_top_level_changed, widget))
        super().addDockWidget(area, widget, area_widget, index)

    def _on_top_level_changed(self, widget, top_level):
        LOGGER.debug(f"{widget}: top_level = {top_level}")
        if not top_level:
            return

        if widget.objectName() == "dummy_widget":
            widget.closeDockWidget()
            return

        area = widget.dockAreaWidget()
        p = QtAds.CDockWidget(self, "dummy_widget")
        p.setWidget(QLabel("Dummy Widget"))
        p.setFeature(QtAds.CDockWidget.DockWidgetFeature.NoTab, True)
        p.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetDeleteOnClose,
            True,
        )
        p.setFeature(QtAds.CDockWidget.DockWidgetFeature.CustomCloseHandling, True)
        widget.dockContainer().addDockWidget(
            QtAds.DockWidgetArea.CenterDockWidgetArea, p, area
        )
        area.setCurrentDockWidget(widget)
        p.topLevelChanged.connect(partial(self._on_top_level_changed, p))
        p.visibilityChanged.connect(partial(self._on_visibility_changed, p))
        p.closeRequested.connect(partial(self._on_close_requested, p))
        p.closed.connect(partial(self._on_closed, p))

        LOGGER.debug(f"{p} created")

    def _on_close_requested(self, widget):
        LOGGER.debug(f"{widget}: close requested")
        widget.closeDockWidget()

    def _on_closed(self, widget):
        LOGGER.debug(f"{widget}: closed")

    def _on_visibility_changed(self, dock_widget, visible):
        areas = -1
        open_widgets = -1
        container = dock_widget.dockContainer()
        if container:
            areas = container.dockAreaCount()
        dock_area = dock_widget.dockAreaWidget()
        if dock_area:
            open_widgets = len(dock_area.openedDockWidgets())
        LOGGER.debug(
            f"{dock_widget}: is visible {visible}. areas: {areas}. open widgets: {open_widgets}"
        )
        if visible and open_widgets == 1 and areas > 1:
            dock_widget.requestCloseDockWidget()
