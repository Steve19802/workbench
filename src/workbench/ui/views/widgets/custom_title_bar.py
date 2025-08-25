from qframelesswindow.titlebar import StandardTitleBar


class CustomTitleBar(StandardTitleBar):
    """Custom title bar"""

    def __init__(self, parent):
        super().__init__(parent)
        self.titleLabel.setAutoFillBackground(True)
