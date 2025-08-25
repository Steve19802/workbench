from ..theme import Theme
from typing import cast
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QInputDialog,
    QMenu,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
import qdarktheme
from qframelesswindow import FramelessMainWindow

from .widgets.custom_main_window import CustomMainWindow
from .widgets.custom_title_bar import CustomTitleBar

import PySide6QtAds as QtAds
from .widgets.custom_dock_manager import CustomDockManager

from .node_editor import NodeEditorWidget


class MainWindow(FramelessMainWindow, CustomMainWindow):
    def __init__(self, parent=None):
        self._theme_controller = Theme()
        super().__init__(parent)

        self.menuView = QMenu("&View")
        self.menubar.addAction(self.menuView.menuAction())
        self.toolBar = self.toolbar

        self.setTitleBar(CustomTitleBar(self))
        self.setWindowTitle("Testing Title")
        self.titleBar.raise_()

        QtAds.CDockManager.setConfigFlag(
            QtAds.CDockManager.FloatingContainerForceNativeTitleBar, True
        )

        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.OpaqueSplitterResize, True)
        QtAds.CDockManager.setConfigFlag(
            QtAds.CDockManager.XmlCompressionEnabled, False
        )
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.FocusHighlighting, True)
        QtAds.CDockManager.setConfigFlag(
            QtAds.CDockManager.TabCloseButtonIsToolButton, True
        )
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.DisableTabTextEliding, True)

        dock_container_widget = QWidget(self)
        dock_container_widget.setObjectName("dockContainer")
        dock_container_layout = QVBoxLayout(dock_container_widget)
        dock_container_layout.setContentsMargins(0, 0, 0, 0)

        self.setCentralWidget(dock_container_widget)
        self.dock_manager = CustomDockManager(dock_container_widget)
        dock_container_layout.addWidget(self.dock_manager)

        node_editor = NodeEditorWidget(parent=self, dock_manager=self.dock_manager)
        self.node_editor = node_editor
        central_dock_widget = QtAds.CDockWidget(self.dock_manager, "CentralWidget")
        central_dock_widget.setWidget(node_editor.graph.widget)
        central_dock_area = self.dock_manager.setCentralWidget(central_dock_widget)
        central_dock_area.setAllowedAreas(QtAds.DockWidgetArea.OuterDockAreas)

        nodestree_dock_widget = QtAds.CDockWidget(self.dock_manager, "Nodes Tree")
        nodestree_dock_widget.setWidget(node_editor.nodes_tree)
        nodestree_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetClosable, False
        )
        nodestree_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetMovable, False
        )
        nodestree_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetFloatable, False
        )

        nodestree_dock_area = self.dock_manager.addDockWidget(
            QtAds.DockWidgetArea.LeftDockWidgetArea, nodestree_dock_widget
        )

        nodeprops_dock_widget = QtAds.CDockWidget(self.dock_manager, "Node Properties")
        nodeprops_dock_widget.setWidget(node_editor.properties_bin)
        nodeprops_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetClosable, False
        )
        nodeprops_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetMovable, False
        )
        nodeprops_dock_widget.setFeature(
            QtAds.CDockWidget.DockWidgetFeature.DockWidgetFloatable, False
        )

        nodeprops_dock_area = self.dock_manager.addDockWidget(
            QtAds.DockWidgetArea.RightDockWidgetArea, nodeprops_dock_widget
        )

        self.create_perspective_ui()
        self.create_simulation_toolbar()
        self.resize(1024, 768)
        self.setMinimumSize(800, 480)

    def create_simulation_toolbar(self):
        icon = self.window().style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        start_processing_action = QAction(icon, "Start Processing", self)
        start_processing_action.triggered.connect(self.node_editor.start_processing)
        icon = self.window().style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        stop_processing_action = QAction(icon, "Stop Processing", self)
        stop_processing_action.triggered.connect(self.node_editor.stop_processing)
        self.toolBar.addSeparator()
        self.toolBar.addAction(start_processing_action)
        self.toolBar.addAction(stop_processing_action)

    def create_perspective_ui(self):
        save_perspective_action = QAction("Create Perspective", self)
        save_perspective_action.triggered.connect(self.save_perspective)
        perspective_list_action = QWidgetAction(self)
        self.perspective_combobox = QComboBox(self)
        self.perspective_combobox.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.perspective_combobox.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.perspective_combobox.activated.connect(self.onPerspectiveActivated)
        perspective_list_action.setDefaultWidget(self.perspective_combobox)
        self.toolBar.addSeparator()
        self.toolBar.addAction(perspective_list_action)
        self.toolBar.addAction(save_perspective_action)

        theme_action = QWidgetAction(self)
        combo_box = QComboBox(self)
        combo_box.addItems(qdarktheme.get_themes())
        combo_box.setCurrentIndex(1)
        combo_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo_box.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        combo_box.currentTextChanged.connect(self._theme_controller.change_theme)
        theme_action.setDefaultWidget(combo_box)

        self.toolBar.addSeparator()
        self.toolBar.addAction(theme_action)

    def onPerspectiveActivated(self, index):
        self.dock_manager.openPerspective(self.dock_manager.perspectiveNames()[index])

    def save_perspective(self):
        perspective_name, ok = QInputDialog.getText(
            self, "Save Perspective", "Enter Unique name:"
        )
        if not ok or not perspective_name:
            return

        self.dock_manager.addPerspective(perspective_name)
        self.perspective_combobox.clear()
        self.perspective_combobox.addItems(self.dock_manager.perspectiveNames())
        self.perspective_combobox.setCurrentText(perspective_name)

    def closeEvent(self, event: QCloseEvent):
        if self.node_editor:
            self.node_editor.stop_processing()
        self.list_windows()
        self.dock_manager.deleteLater()
        super().closeEvent(event)

    def list_windows(self):
        """Gets and prints the list of all top-level windows."""
        # Get the global QApplication instance
        app: QApplication = cast(QApplication, QApplication.instance())

        print("\n--- Current Top-Level Windows ---")
        # Get the list of all widgets with no parent
        top_level_windows = app.topLevelWidgets()

        if not top_level_windows:
            print("No top-level windows found.")
            return

        for i, window in enumerate(top_level_windows):
            if window.__class__.__name__ != "CFloatingDockContainer":
                continue

            window.show()
            # Check if the window is actually visible on screen
            visibility = "Visible" if window.isVisible() else "Hidden"
            print(
                f"{i + 1}: '{window.windowTitle()}' "
                f"({window.__class__.__name__}) - {visibility}"
                f"- {window.size()} - {window.geometry()}"
            )
        print("---------------------------------")
