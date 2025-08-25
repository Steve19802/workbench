from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
import logging

LOGGER = logging.getLogger(__name__)


class CustomMainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        LOGGER.debug("CustomMainWindow(): Creating main window")

        self.setWindowTitle("Custom Main Window")

        master_container = QWidget()

        # Create main layout
        main_layout = QVBoxLayout(master_container)
        main_layout.setContentsMargins(0, 32, 0, 0)
        main_layout.setSpacing(0)
        self._main_layout = main_layout

        # Create the standard components
        self.menubar = QMenuBar()
        self.toolbar = QToolBar("Main Toolbar")
        self.statusbar = QStatusBar()
        self._central_widget_container = QWidget()
        central_layout = QVBoxLayout(self._central_widget_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._central_widget = QLabel("This is the main Content Area")
        self._central_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_layout.addWidget(self._central_widget)

        # Add components to the layout
        main_layout.addWidget(self.menubar)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self._central_widget_container, stretch=1)
        main_layout.addWidget(self.statusbar)

        super().setCentralWidget(master_container)

    def setCentralWidget(self, widget: QWidget) -> None:
        LOGGER.debug(f"setCentralWidget(): {widget}")
        central_layout = self._central_widget_container.layout()
        if central_layout:
            central_layout.removeWidget(self._central_widget)
            central_layout.addWidget(widget)
            self._central_widget = widget

    def dump_object_tree(self, obj: QObject, indent: int = 0):
        """
        Recursively prints the QObject hierarchy starting from a given object.
        """
        # Prepare the indentation string
        indent_str = "  " * indent

        # Get the widget's class name and object name
        class_name = obj.metaObject().className()
        object_name = obj.objectName()

        # Format the output string
        line = f"{indent_str}- {class_name}"
        if object_name:
            line += f" (Name: '{object_name}')"

        # Print the details for the current object
        print(line)

        # Recursively call the function for all children
        for child in obj.children():
            self.dump_object_tree(child, indent + 1)
