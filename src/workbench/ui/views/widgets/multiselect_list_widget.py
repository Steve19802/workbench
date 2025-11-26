from enum import Enum
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem

import logging

LOGGER = logging.getLogger(__name__)

LOGGER.setLevel("DEBUG")

class MultiSelectListWidget(QListWidget):
    """
    A QListWidget subclass that allows multiple selections and
    gets/sets its value as a single, delimited string.
    """

    # A custom signal that emits the selected items as a single string.
    value_changed = Signal(str, str)

    def __init__(self, parent=None, separator: str = ", "):
        super().__init__(parent)
        self._name = None
        self._separator = separator
        
        # Set the selection mode to allow multiple items
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        
        # Connect the signal for when the selection changes
        self.itemSelectionChanged.connect(self._emit_value_changed)

        # Connect item changed
        self.itemChanged.connect(self._item_changed)

    def populate_from_list(self, items: list[str]):
        """Clears the list widget and fills it with string items."""
        self.clear()
        for item in items:
            itm = QListWidgetItem(item)
            itm.setFlags(itm.flags() | Qt.ItemIsUserCheckable)
            itm.setCheckState(Qt.Unchecked)
            self.addItem(itm)
        #self.addItems(items)

    def items(self) -> list[str]:
        """
        Returns all items from the list widget.

        Returns:
            list[str]: list of strings.
        """
        return [self.item(i).text() for i in range(self.count())]

    def set_items(self, items: list[str]):
        """
        Set items on the list widget.

        Args:
            items (list[str]): list of strings.
        """
        self.populate_from_list(items)

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str):
        self._name = name

    def get_separator(self) -> str:
        """Gets the string separator used for joining items."""
        return self._separator

    def set_separator(self, separator: str):
        """Sets the string separator used for joining items."""
        self._separator = separator

    def get_value(self) -> str:
        """Returns the currently selected items as a single delimited string."""
        selected_items = self.selectedIndexes()
        str_list = [str(item.row()) for item in selected_items]
        return self._separator.join(str_list)

    def set_value(self, value: str):
        """Sets the current selection based on a single delimited string."""
        
        # 1. Clear the current selection
        self.clearSelection()

        # 2. Create a set of the string values to select
        if not value:
            items_to_select = set()
        elif type(value) == str:
            items_to_select = set([int(x) for x in value.split(self._separator)])
        elif type(value) == list:
            items_to_select = set(value)
        else:
            items_to_select = set()

        LOGGER.debug(f"items_to_select: {items_to_select}")
        # 3. Iterate over all items and select the ones in the set
        for i in range(self.count()):
            item = self.item(i)
            #if item.text() in items_to_select:
            #    item.setSelected(True)
            if i in items_to_select:
                item.setSelected(True)

    def _item_changed(self, item):
        if item.checkState() == Qt.Checked:
            item.setSelected(True)
        else:
            item.setSelected(False)

    def _emit_value_changed(self):
        """Internal slot to emit the custom valueChanged signal."""
        for index in range(self.count()):
            item = self.item(index)
            if item.isSelected():
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
        # This signal is emitted whenever selection changes
        current_value_str = self.get_value()
        self.value_changed.emit(self._name, current_value_str)
