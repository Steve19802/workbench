from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QFrame
)
import numpy as np
from .measurement_engine import compute_metric
from ....contracts.enums import ScopeModes
from engineering_notation import EngNumber

# --- NUEVO: opciones según modo ---
TIME_METRIC_OPTIONS = [
    "Vpp", "Vrms", "Vavg", "Vmin", "Vmax", "Frequency", "Duty"
]
FREQ_METRIC_OPTIONS = [
    "Fund. Freq.",
    "Fund. Val.",
    "THD",
    "THD+N",
    "SINAD"
]

class MeasurementRow(QWidget):
    selection_changed = Signal()  # Emitir cuando cambia tipo o canal

    def __init__(self, channels: List[str], metric_options: List[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.metric_cbox = QComboBox()
        self.metric_cbox.addItems(metric_options)
        self.metric_cbox.currentIndexChanged.connect(self.selection_changed.emit)

        self.channel_cbox = QComboBox()
        self.channel_cbox.addItems(channels)
        self.channel_cbox.currentIndexChanged.connect(self.selection_changed.emit)

        self.value_lbl = QLabel("—")
        self.value_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        lay.addWidget(self.metric_cbox, 0)
        lay.addWidget(self.channel_cbox, 0)
        lay.addWidget(self.value_lbl, 1)

    def set_channels(self, channels: List[str]):
        self.channel_cbox.blockSignals(True)
        self.channel_cbox.clear()
        self.channel_cbox.addItems(channels)
        self.channel_cbox.blockSignals(False)
        self.selection_changed.emit()

    def set_metric_options(self, opts: List[str]):
        """Recarga el combo de métricas manteniendo la selección si es posible."""
        current = self.metric_name()
        self.metric_cbox.blockSignals(True)
        self.metric_cbox.clear()
        self.metric_cbox.addItems(opts)
        # Intentar mantener la opción si todavía existe
        idx = self.metric_cbox.findText(current)
        self.metric_cbox.setCurrentIndex(idx if idx >= 0 else 0)
        self.metric_cbox.blockSignals(False)
        self.selection_changed.emit()

    def metric_name(self) -> str:
        return self.metric_cbox.currentText()

    def channel_index(self) -> int:
        return self.channel_cbox.currentIndex()

    def set_value(self, val: Optional[float]):
        if val is None or (isinstance(val, float) and not np.isfinite(val)):
            self.value_lbl.setText("—")
            return

        name = self.metric_name()
        if name == "Fund. Freq.":
            self.value_lbl.setText(f"{EngNumber(val, separator= " ")}Hz")
        elif name == "Duty":
            self.value_lbl.setText(f"{val:.3f} %")
        elif name in ("THD", "THD+N"):
            # Mostrar como porcentaje
            self.value_lbl.setText(f"{val:.3f} %")
        elif name == "SINAD":
            # Mostrar en dB
            self.value_lbl.setText(f"{val:.2f} dB")
        else:
            self.value_lbl.setText(f"{EngNumber(val)}")

class MeasurementsPanel(QWidget):
    max_rows = 5
    use_cursors_changed = Signal(bool)

    def __init__(self, channels: List[str] = None, parent: Optional[QWidget] = None, mode: ScopeModes = ScopeModes.TIME):
        super().__init__(parent)
        channels = channels or []
        self._channels = channels
        self._rows: List[MeasurementRow] = []
        self._use_cursors = False
        self._x1 = None
        self._x2 = None
        self._duty_threshold = None
        self._mode = mode  # "time" | "freq"
        self.spectrum_format = 'abs'
        self._build_ui(channels)

    def _metric_options(self) -> List[str]:
        return FREQ_METRIC_OPTIONS if self._mode == ScopeModes.SPECTRUM else TIME_METRIC_OPTIONS

    def _build_ui(self, channels):
        main = QVBoxLayout(self)
        main.setContentsMargins(6, 6, 6, 6)
        main.setSpacing(6)

        header = QGridLayout()
        # Rehabilitamos el checkbox de cursores (útil para banda en THD+N/SINAD)
        # self.ck_use_cursors = QCheckBox("Measure between cursors")
        # self.ck_use_cursors.stateChanged.connect(
        #     lambda s: self._on_use_cursors(s == Qt.Checked)
        # )
        # header.addWidget(self.ck_use_cursors, 0, 0, 1, 2)
        main.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
        main.addWidget(sep)

        self.rows_container = QVBoxLayout()
        self.rows_container.setSpacing(4)
        main.addLayout(self.rows_container)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_remove = QPushButton("Remove last")
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_remove)
        main.addLayout(btns)

        main.addWidget(sep)

        self._add_row()

    def _on_use_cursors(self, enabled: bool):
        self._use_cursors = enabled
        self.use_cursors_changed.emit(enabled)

    def set_mode(self, mode: ScopeModes):
        if mode not in ScopeModes:
            return
        self._mode = mode
        opts = self._metric_options()
        for r in self._rows:
            r.set_metric_options(opts)

    def set_format(self, format: str):
        if format == 'db' or format == 'abs':
            self.spectrum_format = format

    # API que usará el GraphControllerWidget
    def set_channels(self, names: List[str]):
        self._channels = names
        for r in self._rows:
            r.set_channels(names)

    def set_cursor_positions(self, x1: Optional[float], x2: Optional[float]):
        self._x1, self._x2 = x1, x2

    def set_duty_threshold(self, thr: Optional[float]):
        self._duty_threshold = thr

    def update_data(self, x: np.ndarray, y2d: np.ndarray):
        """Refresca todas las filas con los datos actuales."""
        if y2d is None or y2d.ndim != 2:
            return
        for r in self._rows:
            ch = r.channel_index()
            if ch < 0 or ch >= y2d.shape[1]:
                r.set_value(None)
                continue
            val = compute_metric(
                r.metric_name(),
                x, y2d[:, ch],
                x1=self._x1 if self._use_cursors else None,
                x2=self._x2 if self._use_cursors else None,
                spectrum_format= self.spectrum_format,
                duty_threshold=self._duty_threshold,
                domain=self._mode
            )
            r.set_value(val)

    # Gestión de filas
    def _add_row(self):
        if len(self._rows) >= self.max_rows:
            self.btn_add.setEnabled(False)
            return
        row = MeasurementRow(self._channels, self._metric_options())
        # row.selection_changed.connect(lambda: None)
        self.rows_container.addWidget(row)
        self._rows.append(row)
        if len(self._rows) >= self.max_rows:
            self.btn_add.setEnabled(False)
        self.btn_remove.setEnabled(True)

    def _remove_row(self):
        if not self._rows:
            self.btn_remove.setEnabled(False)
            return
        row = self._rows.pop()
        row.setParent(None)
        row.deleteLater()
        self.btn_add.setEnabled(True)
        if not self._rows:
            self.btn_remove.setEnabled(False)