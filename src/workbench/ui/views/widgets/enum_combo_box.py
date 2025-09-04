from enum import Enum
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


class EnumComboBox(QComboBox):
    """
    A QComboBox subclass that is specifically designed to work with Python Enums.
    It stores the actual Enum member in the item data.
    """

    # A custom signal that emits the selected Enum member object.
    value_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = None
        self.currentIndexChanged.connect(self._emit_value_changed)

    def populate_from_enum(self, enum_class: type[Enum]):
        """Clears the combo box and fills it with members from an Enum."""
        self.clear()
        for member in enum_class:
            # Display the member's user-friendly value (its string)
            # Store the actual Enum member object as the item's data
            self.addItem(member.value, userData=member)

    def items(self):
        """
        Returns items from the combobox.

        Returns:
            list[str]: list of strings.
        """
        return [self.itemText(i) for i in range(self.count())]

    def set_items(self, items):
        """
        Set items on the combobox.

        Args:
            items (list[str]): list of strings.
        """
        self.populate_from_enum(items)

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_value(self) -> Enum:
        """Returns the currently selected Enum member."""
        return self.currentData()

    def set_value(self, value: Enum):
        """Sets the current item based on an Enum member."""
        index = self.findData(value)
        if index != -1:
            self.setCurrentIndex(index)

    def _emit_value_changed(self, index: int):
        """Internal slot to emit the custom valueChanged signal."""
        enum_member = self.itemData(index)
        if enum_member:
            self.value_changed.emit(self._name, enum_member)
