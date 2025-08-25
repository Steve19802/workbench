from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget


class ControlPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_orientation = None

        # Store a list of the widgets we need to manage
        self.widgets = []

    def addControlWidget(self, widget):
        """Adds a control widget to be managed by this panel's layout."""
        self.widgets.append(widget)

    def setOrientation(self, orientation):
        """
        Switches the internal layout between horizontal and vertical.

        Args:
            orientation (Qt.Orientation): The new orientation.
        """
        # Only rebuild the layout if the orientation has changed
        if orientation == self.current_orientation:
            return

        self.current_orientation = orientation

        # If a layout already exists, delete it
        if self.layout() is not None:
            # Clear all items from the layout before deleting it
            while self.layout().count():
                item = self.layout().takeAt(0)
                # Important: check if it's a widget before deleting
                if item.widget():
                    item.widget().setParent(None)
            QWidget().setLayout(self.layout())  # Properly delete old layout

        # Create the new layout based on the orientation
        if orientation == Qt.Orientation.Horizontal:
            new_layout = QHBoxLayout(self)
        else:  # Vertical
            new_layout = QVBoxLayout(self)

        # Add all the stored widgets to the new layout
        for widget in self.widgets:
            new_layout.addWidget(widget)
        new_layout.addStretch()
