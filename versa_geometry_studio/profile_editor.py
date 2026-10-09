"""Explicit profile calibration editor; structured JSON covers per-objective data."""
from dataclasses import asdict, replace
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QCheckBox, QComboBox, QDialogButtonBox, QMessageBox,
    QHeaderView)
from .models import BOUND_KEYS, Quantity, CoordinateMapping
from .persistence import profile_from_dict
from .controls import label, NumberEdit


class ProfileEditor(QDialog):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile, self.result_profile = profile, None
        self.setWindowTitle("Instrument profile · calibration and provenance")
        self.resize(880, 640)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Only confirmed physical bounds constrain the solver. Unknown fields stay blank.", "muted", True))
        tabs = QTabWidget(); layout.addWidget(tabs)
        general = QWidget(); form = QFormLayout(general)
        self.name = QLineEdit(profile.name)
        self.notes = QPlainTextEdit(profile.notes)
        self.focal = NumberEdit(profile.focal_spot_um.value, True)
        form.addRow("Profile name", self.name)
        form.addRow("Focal spot diameter (µm), optional", self.focal)
        form.addRow("Notes / local calibration records", self.notes)
        tabs.addTab(general, "Profile")
        self.table = QTableWidget(len(BOUND_KEYS), 6)
        self.table.setHorizontalHeaderLabels(("Physical bound", "Value (mm)", "Confirmed", "Provenance", "Source / version", "Date"))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, key in enumerate(BOUND_KEYS):
            q = profile.bounds.get(key, Quantity())
            item = QTableWidgetItem(key); item.setFlags(item.flags() & ~item.flags().ItemIsEditable)
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem("" if q.value is None else repr(q.value)))
            confirmed = QCheckBox(); confirmed.setChecked(q.confirmed); self.table.setCellWidget(row, 2, confirmed)
            origin = QComboBox(); origin.addItems(("user supplied", "nominal", "calibrated", "reference")); origin.setCurrentText(q.origin)
            self.table.setCellWidget(row, 3, origin)
            self.table.setItem(row, 4, QTableWidgetItem(q.source + (" | "+q.version if q.version else "")))
            self.table.setItem(row, 5, QTableWidgetItem(q.date))
        tabs.addTab(self.table, "Physical bounds")
        mapping = QWidget(); form = QFormLayout(mapping)
        form.addRow(label("Documented signed stage separation = cₐ a + cᵦ b + offset.\nDo not guess signs, offsets, or coordinate meanings.", "muted", True))
        self.mapping_verified = QCheckBox("Mapping verified against local calibration")
        self.mapping_verified.setChecked(profile.mapping.verified)
        self.map_a = NumberEdit(profile.mapping.coeff_a, True)
        self.map_b = NumberEdit(profile.mapping.coeff_b, True)
        self.map_offset = NumberEdit(profile.mapping.offset_mm, True)
        self.map_source = QLineEdit(profile.mapping.source)
        self.legacy_confirmed = QCheckBox("135 mm legacy stage rule confirmed for this installed 0.4× objective")
        self.legacy_confirmed.setChecked(profile.legacy_stage_min.confirmed)
        form.addRow(self.mapping_verified)
        form.addRow("cₐ (dimensionless)", self.map_a)
        form.addRow("cᵦ (dimensionless)", self.map_b)
        form.addRow("Offset (mm)", self.map_offset)
        form.addRow("Calibration reference / date", self.map_source)
        form.addRow(self.legacy_confirmed)
        form.addRow(label("Legacy ZEISS v11.x Table 2-3; applied only when BOTH confirmation and mapping verification are present. It never silently becomes D ≥ 135 mm.", "muted", True))
        tabs.addTab(mapping, "Stage mapping")
        objective = QWidget(); obj_layout = QVBoxLayout(objective)
        obj_layout.addWidget(label("Each objective owns its camera calibration, usable rectangle/image circle, binning, crop, parity, availability, restrictions, and provenance. Edit the structured data below; null means unconfigured. Bounds use the same Quantity records as the physical-bounds tab.", "muted", True))
        self.objectives = QPlainTextEdit(json.dumps({k: asdict(v) for k, v in profile.objectives.items()}, indent=2, ensure_ascii=False))
        self.objectives.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        obj_layout.addWidget(self.objectives)
        tabs.addTab(objective, "Objective calibrations (JSON)")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Validate & apply")
        buttons.accepted.connect(self.validate_accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_accept(self):
        try:
            raw = asdict(self.profile)
            raw['name'], raw['notes'] = self.name.text(), self.notes.toPlainText()
            raw['objectives'] = json.loads(self.objectives.toPlainText())
            bounds = {}
            for row, key in enumerate(BOUND_KEYS):
                text = self.table.item(row, 1).text().strip()
                source_version = self.table.item(row, 4).text().split(" | ", 1)
                bounds[key] = asdict(Quantity(float(text) if text else None, "mm", self.table.cellWidget(row, 3).currentText(),
                    self.table.cellWidget(row, 2).isChecked(), source_version[0], source_version[1] if len(source_version)>1 else "", self.table.item(row, 5).text()))
            raw['bounds'] = bounds
            raw['mapping'] = asdict(CoordinateMapping(self.mapping_verified.isChecked(), self.map_a.parsed(), self.map_b.parsed(), self.map_offset.parsed(), self.map_source.text()))
            raw['legacy_stage_min']['confirmed'] = self.legacy_confirmed.isChecked()
            raw['focal_spot_um'] = asdict(replace(self.profile.focal_spot_um, value=self.focal.parsed(), origin="user supplied"))
            self.result_profile = profile_from_dict(raw)
        except (ValueError, TypeError, KeyError) as exc:
            QMessageBox.warning(self, "Profile needs correction", str(exc))
            return
        self.accept()
