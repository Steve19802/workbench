from PySide6.QtWidgets import QDoubleSpinBox


class CursorAwareDoubleSpinBox(QDoubleSpinBox):
    """
    A QDoubleSpinBox that adjusts its step size based on the
    cursor's position within the text.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # We don't use the default singleStep property, but set it for clarity.
        self.setSingleStep(0.01)

    def stepBy(self, steps):
        """
        Overrides the default step behavior to be cursor-aware.
        """
        # Get the internal line edit widget
        line_edit = self.lineEdit()
        text = line_edit.text()
        text_len = len(text)
        cursor_pos = line_edit.cursorPosition()

        # if the cursor is at the begining of the value
        # we move one position to the right to not
        # create a new digit
        if cursor_pos == 0:
            cursor_pos += 1
            line_edit.setCursorPosition(cursor_pos)

        # if the cursor is just before the minu sign
        # we move one position to the right to not break
        # the number
        if (text.find("-") + 1) == cursor_pos:
            cursor_pos += 1
            line_edit.setCursorPosition(cursor_pos)

        # Find the position of the decimal point
        try:
            decimal_point_pos = text.index(".")
        except ValueError:
            # If no decimal point, treat it as being at the end
            decimal_point_pos = len(text)

        # Calculate the power of 10 based on cursor position
        if cursor_pos > decimal_point_pos:
            # Cursor is in the fractional part
            exponent = decimal_point_pos - (cursor_pos - 1)
        else:
            # Cursor is in the integer part
            exponent = decimal_point_pos - cursor_pos

        # Calculate the dynamic step value
        dynamic_step = 10**exponent

        # Call the original stepBy method with our dynamic step
        # We multiply our dynamic_step by the original singleStep() to
        # allow for fractional base steps if needed (e.g., 0.5, 0.2).
        # For a pure 1, 10, 100 step, you could just use dynamic_step.
        self.setSingleStep(dynamic_step)
        super().stepBy(steps)
        # Restore a default step if desired
        self.setSingleStep(0.01)
        cursor_pos += len(line_edit.text()) - text_len
        line_edit.setCursorPosition(cursor_pos)
