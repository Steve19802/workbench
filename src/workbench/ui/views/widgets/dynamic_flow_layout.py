from PySide6.QtWidgets import QLayout, QSizePolicy
from PySide6.QtCore import QRect, QPoint, QSize, Qt


class DynamicFlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._central_widget = None
        self._side_widget = None

    def setCentralWidget(self, widget):
        self._central_widget = widget
        self.addWidget(widget)

    def setSideWidget(self, widget):
        self._side_widget = widget
        self.addWidget(widget)

    # --- Standard QLayout boilerplate ---
    def addItem(self, item):
        # We handle widgets directly, so this is not used
        pass

    def count(self):
        count = 0
        if self._central_widget:
            count += 1
        if self._side_widget:
            count += 1
        return count

    def itemAt(self, index):
        if index == 0 and self._central_widget:
            return self._central_widget.layout().itemAt(0)
        if index == 1 and self._side_widget:
            return self._side_widget.layout().itemAt(0)
        return None

    def takeAt(self, index):
        # This layout does not support removing items
        return None

    def sizeHint(self):
        # A basic size hint, can be improved
        return QSize(400, 200)

    def setGeometry(self, rect):
        """This is the core logic that rearranges the widgets."""
        super().setGeometry(rect)

        if not self._central_widget or not self._side_widget:
            return

        # Determine orientation based on aspect ratio
        is_landscape = rect.width() > rect.height()
        if is_landscape:
            # --- LANDSCAPE MODE ---
            # Tell the control panel to use a VERTICAL layout
            self._side_widget.setOrientation(Qt.Orientation.Vertical)

            side_width = self._side_widget.sizeHint().width()
            plot_rect = QRect(
                rect.topLeft(), QSize(rect.width() - side_width, rect.height())
            )
            side_rect = QRect(
                QPoint(plot_rect.right(), rect.top()), QSize(side_width, rect.height())
            )

            self._central_widget.setGeometry(plot_rect)
            self._side_widget.setGeometry(side_rect)
        else:
            # --- PORTRAIT MODE ---
            # Tell the control panel to use a HORIZONTAL layout
            self._side_widget.setOrientation(Qt.Orientation.Horizontal)

            side_height = self._side_widget.sizeHint().height()
            plot_rect = QRect(
                rect.topLeft(), QSize(rect.width(), rect.height() - side_height)
            )
            side_rect = QRect(
                QPoint(rect.left(), plot_rect.bottom()),
                QSize(rect.width(), side_height),
            )

            self._central_widget.setGeometry(plot_rect)
            self._side_widget.setGeometry(side_rect)
