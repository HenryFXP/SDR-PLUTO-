"""Reusable control widgets with large fonts."""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from .big_label import apply_big_font

__all__ = ["LabeledSlider", "LabeledComboBox", "LabeledSpinBox", "FlexFormLayout"]


class FlexFormLayout(QtWidgets.QFormLayout):
    """A form layout that enforces uniform label sizing and padding."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLabelAlignment(QtCore.Qt.AlignRight)
        self.setHorizontalSpacing(18)
        self.setVerticalSpacing(12)


class LabeledSlider(QtWidgets.QWidget):
    """Slider with an attached label showing the current value."""

    value_changed = QtCore.pyqtSignal(float)

    def __init__(
        self,
        minimum: float,
        maximum: float,
        step: float,
        unit: str = "",
        orientation: QtCore.Qt.Orientation = QtCore.Qt.Horizontal,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._unit = unit
        self._multiplier = 1.0 / step if step else 1.0

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.slider = QtWidgets.QSlider(orientation)
        self.slider.setRange(int(minimum * self._multiplier), int(maximum * self._multiplier))
        self.slider.valueChanged.connect(self._emit_value)
        layout.addWidget(self.slider, 1)

        self.label = QtWidgets.QLabel("0")
        apply_big_font(self.label, 12)
        self.label.setMinimumWidth(90)
        layout.addWidget(self.label)

    def _emit_value(self, raw_value: int) -> None:
        value = raw_value / self._multiplier
        self.label.setText(f"{value:.2f} {self._unit}".strip())
        self.value_changed.emit(value)

    def set_value(self, value: float) -> None:
        self.slider.setValue(int(value * self._multiplier))
        self._emit_value(self.slider.value())


class LabeledSpinBox(QtWidgets.QWidget):
    """High visibility spin box with label."""

    value_changed = QtCore.pyqtSignal(float)

    def __init__(
        self,
        minimum: float,
        maximum: float,
        step: float,
        suffix: str = "",
        decimals: int = 2,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(f" {suffix}" if suffix else "")
        apply_big_font(self.spin, 12)
        self.spin.valueChanged.connect(self.value_changed)
        layout.addWidget(self.spin)

    def set_value(self, value: float) -> None:
        self.spin.setValue(value)

    def value(self) -> float:
        return self.spin.value()


class LabeledComboBox(QtWidgets.QWidget):
    """Combo box with prominent text."""

    current_index_changed = QtCore.pyqtSignal(int)

    def __init__(self, label: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text_label = QtWidgets.QLabel(label)
        apply_big_font(text_label, 12)
        layout.addWidget(text_label)

        self.combo = QtWidgets.QComboBox()
        apply_big_font(self.combo, 12)
        self.combo.currentIndexChanged.connect(self.current_index_changed)
        layout.addWidget(self.combo, 1)

    def add_items(self, items: list[str]) -> None:
        self.combo.addItems(items)

    def current_text(self) -> str:
        return self.combo.currentText()

    def set_current_index(self, index: int) -> None:
        self.combo.setCurrentIndex(index)
