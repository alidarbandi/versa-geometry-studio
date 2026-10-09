from PySide6.QtCore import Signal, QSignalBlocker, Qt
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout, QSlider, QFrame, QScrollArea
import math


def label(text, name=None, wrap=False):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def panel():
    w = QFrame()
    w.setObjectName("panel")
    return w


def scroll(widget):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(widget)
    return area


class NumberEdit(QLineEdit):
    committed = Signal(object)

    def __init__(self, value, optional=False, integer=False, parent=None):
        super().__init__(parent)
        self.optional, self.integer = optional, integer
        self.value = value
        self.set_value(value)
        self.setPlaceholderText("Unconfigured" if optional else "Value")
        self.editingFinished.connect(self._commit)
        self.textEdited.connect(self._validate_text)
        self.setMinimumWidth(65)
        self.setMaximumWidth(160)

    def set_value(self, value):
        self.value = value
        with QSignalBlocker(self):
            self.setText("" if value is None else format(value, ".10g"))
        self.setProperty("invalid", False)
        self.setToolTip("Unconfigured" if value is None else repr(value))
        self.style().unpolish(self); self.style().polish(self)

    def parsed(self):
        text = self.text().strip()
        if not text and self.optional:
            return None
        number = float(text)
        if not math.isfinite(number) or (self.integer and not number.is_integer()):
            raise ValueError("Enter a finite " + ("integer" if self.integer else "number"))
        return int(number) if self.integer else number

    def _validate_text(self):
        try:
            self.parsed()
            invalid = False
        except ValueError:
            invalid = True
        self.setProperty("invalid", invalid)
        self.style().unpolish(self); self.style().polish(self)

    def _commit(self):
        if not self.isModified():
            return
        try:
            value = self.parsed()
        except ValueError:
            self.setToolTip("Enter a finite number; the scene retains its last valid value")
            return
        self.setModified(False)
        if value != self.value:
            self.committed.emit(value)


class DistanceControl(QWidget):
    moved = Signal(str, float)
    drag_started = Signal()
    drag_finished = Signal()

    def __init__(self, which, title, value):
        super().__init__()
        self.which = which
        self.value = value
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 8)
        row = QHBoxLayout()
        row.addWidget(label(title, "muted"))
        row.addStretch()
        self.edit = NumberEdit(value)
        self.edit.setMaximumWidth(110)
        row.addWidget(self.edit)
        row.addWidget(label("mm", "muted"))
        layout.addLayout(row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(10, 50000)
        self.slider.setValue(round(value*100))
        self.slider.setSingleStep(1)
        self.slider.setPageStep(100)
        self.slider.setToolTip("Model exploration range 0.1–500 mm; not manufacturer travel. Arrow keys: 0.01 mm.")
        layout.addWidget(self.slider)
        self.edit.committed.connect(lambda v: self.moved.emit(which, v))
        self.slider.valueChanged.connect(lambda v: self.moved.emit(which, v/100))
        self.slider.sliderPressed.connect(self.drag_started)
        self.slider.sliderReleased.connect(self.drag_finished)

    def set_value(self, value):
        self.value = value
        self.edit.set_value(value)
        with QSignalBlocker(self.slider):
            self.slider.setMaximum(max(50000, math.ceil(value*110)))
            self.slider.setMinimum(min(10, max(1, math.floor(value*100))))
            self.slider.setValue(round(value*100))


class MetricCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 9, 13, 10)
        layout.setSpacing(2)
        layout.addWidget(label(title, "muted"))
        self.value = label("—", "metric")
        layout.addWidget(self.value)
        self.detail = label("", "muted")
        layout.addWidget(self.detail)

    def update_value(self, text, detail, tooltip):
        self.value.setText(text)
        self.detail.setText(detail)
        self.setToolTip(tooltip)
