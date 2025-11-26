import logging
from PySide6.QtCore import QLocale, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from workbench.contracts.enums import ScaleMode

from .cursor_aware_double_spinbox import CursorAwareDoubleSpinBox
from ...viewmodels.scope_viewmodel import ScopeViewModel

LOGGER = logging.getLogger(__name__)

LOGGER.setLevel("DEBUG")


class ScaleControlWidget(QWidget):
    """
    A view that provides UI controls for a ScaleController ViewModel.
    It is now a "dumb" component that reflects the state of its ViewModel.
    """

    STYLESHEET = """
        /* Style for the container of the button group */
                    
        /* Round the left corners of the first button */
        QPushButton#firstButton {
            border-top-left-radius: 3px;
            border-bottom-left-radius: 3px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
        }

        /* Round the right corners of the last button */
        QPushButton#lastButton {
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        
        /* Add a border for middle buttons */
        QPushButton#middleButton {
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
        }
    """

    def __init__(self, view_model: ScopeViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        self._build_ui()
        self._bind_view_model()
        self.on_view_model_state_updated()  # Set initial UI state

    def _build_ui(self):
        self.setStyleSheet(self.STYLESHEET)
        layout = QVBoxLayout(self)

        # --- Mode selection buttons ---
        btn_grp_layout = QHBoxLayout()
        btn_grp_layout.setSpacing(0)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        items = [
            ("Manual", ScaleMode.MANUAL),
            ("Auto", ScaleMode.AUTOMATIC),
            ("Auto Range", ScaleMode.AUTO_RANGE),
        ]
        for i, (text, mode) in enumerate(items):
            button = QPushButton(text)
            button.setProperty("scale_mode", mode)  # Store mode on the button
            button.setCheckable(True)
            # Set object names for styling
            if i == 0:
                button.setObjectName("firstButton")
            elif i == len(items) - 1:
                button.setObjectName("lastButton")
            else:
                button.setObjectName("middleButton")
            btn_grp_layout.addWidget(button)
            self.button_group.addButton(button)
        layout.addLayout(btn_grp_layout)

        # --- Manual controls container ---
        self._manual_container = QWidget()
        manual_layout = QHBoxLayout(self._manual_container)
        manual_layout.setContentsMargins(5, 0, 0, 0)

        self._min_spinbox = CursorAwareDoubleSpinBox()
        self._min_spinbox.setLocale(QLocale.c())
        self._min_spinbox.setRange(-10000.0, 10000.0)
        self._min_spinbox.setDecimals(2)
        self._min_spinbox.setSingleStep(0.1)
        self._min_spinbox.setValue(-1.0)
        self._min_spinbox.valueChanged.connect(self._on_manual_limits_changed)

        self._max_spinbox = CursorAwareDoubleSpinBox()
        self._max_spinbox.setLocale(QLocale.c())
        self._max_spinbox.setRange(-10000.0, 10000.0)
        self._max_spinbox.setDecimals(2)
        self._max_spinbox.setSingleStep(0.1)
        self._max_spinbox.setValue(1.0)
        self._max_spinbox.valueChanged.connect(self._on_manual_limits_changed)

        manual_layout.addWidget(QLabel("Min:"))
        manual_layout.addWidget(self._min_spinbox)
        manual_layout.addWidget(QLabel("Max:"))
        manual_layout.addWidget(self._max_spinbox)
        layout.addWidget(self._manual_container)

    def _bind_view_model(self):
        """Connects View events to the ViewModel and vice-versa."""
        # --- ViewModel -> View Connections ---
        # When the ViewModel's state changes, update the entire UI.
        self.view_model.view_vertical_scale_mode_changed.connect(
            self.on_view_model_state_updated
        )

        # --- View -> ViewModel Connections ---
        # When the user clicks a button, update the ViewModel's mode property.
        self.button_group.buttonClicked.connect(self._on_mode_button_clicked)

        # When the user changes a spinbox, update the ViewModel's manual properties.
        self._min_spinbox.valueChanged.connect(self._on_manual_limits_changed)
        self._max_spinbox.valueChanged.connect(self._on_manual_limits_changed)

    @Slot()
    def on_view_model_state_updated(self):
        """Pulls all state from the ViewModel and updates the UI."""
        if self.sender() != self.view_model:
            return

        LOGGER.debug("updating state from view_model")
        # Update which mode button is checked
        current_mode = self.view_model.get_property("vertical_scale_mode")
        LOGGER.debug(f"ViewModel scale_mode: {current_mode}")
        for button in self.button_group.buttons():
            LOGGER.debug(f"buttons mode: {button.property('scale_mode')}")
            if button.property("scale_mode") == current_mode:
                button.setChecked(True)
                break

        # Update visibility and values of manual controls
        is_manual = current_mode == ScaleMode.MANUAL
        self._manual_container.setEnabled(is_manual)

        # Block signals to prevent feedback loops while setting values
        self._min_spinbox.blockSignals(True)
        self._max_spinbox.blockSignals(True)
        self._min_spinbox.setValue(self.view_model.get_property("vertical_scale_min"))
        self._max_spinbox.setValue(self.view_model.get_property("vertical_scale_max"))
        self._min_spinbox.blockSignals(False)
        self._max_spinbox.blockSignals(False)

    @Slot(QPushButton)
    def _on_mode_button_clicked(self, button):
        """Pushes the selected mode to the ViewModel."""
        self.view_model.update_property(
            "vertical_scale_mode", button.property("scale_mode")
        )

    @Slot()
    def _on_manual_limits_changed(self):
        """Pushes the spinbox values to the ViewModel."""
        LOGGER.debug("Updating view_model property")
        # We must set both properties, even if only one changed.
        self.view_model.update_property("vertical_scale_min", self._min_spinbox.value())
        self.view_model.update_property("vertical_scale_max", self._max_spinbox.value())
