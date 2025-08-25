import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Slot
from typing import List, Sequence

# I've assumed you are using PySide6 based on our previous conversations.
# If you are using PyQt5, just change the import statements back.


class LegendSelect(QtCore.QObject):
    """
    Creates and manages a legend of curves with checkboxes to show/hide them.
    The legend can be dynamically updated with a new set of curves.

    The UI is contained in the 'widget' attribute, which should be added
    to your layout.
    """

    class PaintedBox(QtWidgets.QWidget):
        """Draws a rectangle with a line inside to represent a curve's pen."""

        def __init__(self, pen, box_bg_color, box_width, box_height, parent=None):
            super().__init__(parent=parent)
            self.pen = pen
            self.box_bg_color = box_bg_color
            self.setFixedSize(box_width, box_height)

        def paintEvent(self, _event):
            w = self.width()
            h = self.height()
            x_offset, y_offset = 8, 6

            painter = QtGui.QPainter(self)
            painter.fillRect(self.rect(), self.box_bg_color)
            painter.setPen(self.pen)
            painter.drawLine(x_offset, h - y_offset, w - x_offset, y_offset)
            painter.end()

    def __init__(
        self,
        hide_toggle_button: bool = False,
        box_bg_color: QtGui.QColor = QtGui.QColor(0, 0, 0),
        box_width: int = 40,
        box_height: int = 23,
        parent=None,
    ):
        super().__init__(parent=parent)

        # --- Store configuration ---
        self._box_bg_color = box_bg_color
        self._box_width = box_width
        self._box_height = box_height

        # --- Internal state ---
        self._linked_curves: List[pg.PlotDataItem] = []
        self.chkbs: List[QtWidgets.QCheckBox] = []
        self.painted_boxes: List[LegendSelect.PaintedBox] = []

        # --- Setup persistent UI elements (that don't change) ---
        # Main widget and its layout
        self.widget = QtWidgets.QWidget()
        self._main_layout = QtWidgets.QVBoxLayout(self.widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(4)

        # A container for the dynamically generated curve rows
        self._curves_widget = QtWidgets.QWidget()
        self._curves_layout = QtWidgets.QVBoxLayout(self._curves_widget)
        self._curves_layout.setContentsMargins(0, 0, 0, 0)
        self._curves_layout.setSpacing(1)

        # The "No Data" label
        self._lbl_no_data = QtWidgets.QLabel("No Data Series")
        self._lbl_no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # The toggle button
        self.qpbt_toggle = QtWidgets.QPushButton("Show / Hide All")
        self.qpbt_toggle.clicked.connect(self.toggle)
        self.qpbt_toggle.setHidden(hide_toggle_button)

        # Add persistent widgets to the main layout
        self._main_layout.addWidget(self._lbl_no_data)
        self._main_layout.addWidget(self._curves_widget)
        self._main_layout.addStretch()  # Pushes toggle button to the bottom
        if not hide_toggle_button:
            self._main_layout.addWidget(self.qpbt_toggle)

        # Set the initial empty state
        self.update([])

    def _clear_layout(self, layout):
        """Recursively clears all widgets and sub-layouts from a layout."""
        if layout is None:
            return
        # Iterate backwards to safely remove items
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # If the item is a widget, schedule it for deletion
                widget.deleteLater()
            else:
                # If the item is a nested layout, clear it recursively
                self._clear_layout(item.layout())

    def update(self, linked_curves: Sequence[pg.PlotDataItem]):
        """
        Clears the old legend and rebuilds it with a new list of curves.

        Args:
            linked_curves: A new sequence of pyqtgraph.PlotDataItem instances.
        """
        self._linked_curves = linked_curves

        # --- Clear all dynamically created widgets ---
        self.chkbs.clear()
        self.painted_boxes.clear()
        self._clear_layout(self._curves_layout)

        # --- Handle state based on whether curves exist ---
        if not self._linked_curves:
            self._lbl_no_data.show()
            self._curves_widget.hide()
            self.qpbt_toggle.hide()
            return

        self._lbl_no_data.hide()
        self._curves_widget.show()
        if not self.qpbt_toggle.isHidden():
            self.qpbt_toggle.show()

        # --- Rebuild the legend with the new curves ---
        for curve in self._linked_curves:
            chkb = QtWidgets.QCheckBox(curve.name())
            chkb.setChecked(curve.isVisible())
            chkb.clicked.connect(self._updateVisibility)
            self.chkbs.append(chkb)

            painted_box = self.PaintedBox(
                pen=curve.opts["pen"],
                box_bg_color=self._box_bg_color,
                box_width=self._box_width,
                box_height=self._box_height,
            )
            self.painted_boxes.append(painted_box)

            # Create a layout for each row
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.addWidget(chkb)
            row_layout.addStretch()
            row_layout.addWidget(painted_box)
            self._curves_layout.addLayout(row_layout)

    @Slot()
    def _updateVisibility(self):
        # This method works as before
        for idx, chkb in enumerate(self.chkbs):
            if idx < len(self._linked_curves):
                self._linked_curves[idx].setVisible(chkb.isChecked())

    @Slot()
    def toggle(self):
        # This method works as before
        any_unchecked = any(not chkb.isChecked() for chkb in self.chkbs)

        new_state = True if any_unchecked else False
        for chkb in self.chkbs:
            chkb.setChecked(new_state)

        self._updateVisibility()


class LegendSelect2(QtCore.QObject):
    """Creates and manages a legend of all passed curves with checkboxes to
    show or hide each curve. The legend ends with a push button to show or
    hide all curves in one go. The full set of GUI elements is contained in
    attribute ``grid`` of type ``PyQt5.QtWidget.QGridLayout`` to be added to
    your GUI.

    Example grid::

        □ Curve 1  [  /  ]
        □ Curve 2  [  /  ]
        □ Curve 3  [  /  ]
        [ Show / Hide all]

    The initial visibility, name and pen of each curve will be retrieved
    from the members within the passed curves, i.e.:

        * ``curve.isVisible()``
        * ``curve.name()``
        * ``curve.opts["pen"]``

    Args:
        linked_curves (``Sequence[pyqtgraph.PlotDataItem | ThreadSafeCurve]``):
            Sequence of ``pyqtgraph.PlotDataItem`` or ``ThreadSafeCurve``
            instances to be controlled by the legend.

        hide_toggle_button (``bool``, optional):
            Default: False

        box_bg_color (``QtGui.QColor``, optional):
            Background color of the legend boxes.

            Default: ``QtGui.QColor(0, 0, 0)``

        box_width (``int``, optional):
            Default: 40

        box_height (``int``, optional):
            Default: 23

    Attributes:
        chkbs (``List[PyQt5.QtWidgets.QCheckbox]``):
            List of checkboxes to control the visiblity of each curve.

        painted_boxes (``List[PyQt5.QtWidgets.QWidget]``):
            List of painted boxes illustrating the pen of each curve.

        qpbt_toggle (``PyQt5.QtWidgets.QPushButton``):
            Push button instance that toggles showing/hiding all curves in
            one go.

        grid (``PyQt5.QtWidgets.QGridLayout``):
            The full set of GUI elements combined into a grid to be added
            to your GUI.
    """

    def __init__(
        self,
        linked_curves: Sequence[pg.PlotDataItem],
        hide_toggle_button: bool = False,
        box_bg_color: QtGui.QColor = QtGui.QColor(0, 0, 0),
        box_width: int = 40,
        box_height: int = 23,
        parent=None,
    ):
        super().__init__(parent=parent)

        self._linked_curves = linked_curves
        self.chkbs: List[QtWidgets.QCheckBox] = []
        self.painted_boxes: List[LegendSelect.PaintedBox] = []
        self.grid = QtWidgets.QGridLayout()  # The full set of GUI elements
        self.grid.setSpacing(1)

        if self._linked_curves is None:
            lbl = QtWidgets.QLabel("No Data Series")
            self.grid.addWidget(lbl, 0, 0)
            return

        for idx, curve in enumerate(self._linked_curves):
            chkb = QtWidgets.QCheckBox(curve.name())
            chkb.setChecked(curve.isVisible())
            chkb.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self.chkbs.append(chkb)
            # fmt: off
            chkb.clicked.connect(lambda: self._updateVisibility())  # pylint: disable=unnecessary-lambda
            # fmt: on

            painted_box = self.PaintedBox(
                pen=curve.opts["pen"],
                box_bg_color=box_bg_color,
                box_width=box_width,
                box_height=box_height,
            )
            self.painted_boxes.append(painted_box)

            p = {"alignment": Qt.AlignmentFlag.AlignLeft}
            self.grid.addWidget(chkb, idx, 0, **p)
            p = {"alignment": Qt.AlignmentFlag.AlignRight}
            self.grid.addWidget(painted_box, idx, 1, **p)
            # self.grid.setColumnStretch(0, 1)
            # self.grid.setColumnStretch(1, 0)
            self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not hide_toggle_button:
            self.qpbt_toggle = QtWidgets.QPushButton("Show / Hide all")
            self.grid.addItem(QtWidgets.QSpacerItem(0, 10), self.grid.rowCount(), 0)
            self.grid.addWidget(self.qpbt_toggle, self.grid.rowCount(), 0, 1, 2)
            self.qpbt_toggle.clicked.connect(self.toggle)

    @Slot()
    def _updateVisibility(self):
        for idx, chkb in enumerate(self.chkbs):
            self._linked_curves[idx].setVisible(chkb.isChecked())

    @Slot()
    def toggle(self):
        """First: If any checkbox is unchecked  --> check all.
        Second: If all checkboxes are checked --> uncheck all."""
        any_unchecked = False
        for chkb in self.chkbs:
            if not chkb.isChecked():
                chkb.setChecked(True)
                any_unchecked = True

        if not any_unchecked:
            for chkb in self.chkbs:
                chkb.setChecked(False)

        self._updateVisibility()

    class PaintedBox(QtWidgets.QWidget):
        """GUI element belonging to ``LegendSelect()``. Draws a rectangle with a
        line drawn inside according to the passed pen settings. This is used to
        build up the rows of the legend."""

        def __init__(self, pen, box_bg_color, box_width, box_height, parent=None):
            super().__init__(parent=parent)

            self.pen = pen
            self.box_bg_color = box_bg_color

            self.setFixedWidth(box_width)
            self.setFixedHeight(box_height)

        def paintEvent(self, _event):
            w = self.width()
            h = self.height()
            x = 8  # offset line
            y = 6  # offset line

            painter = QtGui.QPainter()
            painter.begin(self)
            painter.fillRect(0, 0, w, h, self.box_bg_color)
            painter.setPen(self.pen)
            painter.drawLine(QtCore.QLine(x, h - y, w - x, y))
            painter.end()
