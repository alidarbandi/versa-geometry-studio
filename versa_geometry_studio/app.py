"""Desktop application composition. Model calculations live outside the UI."""
from dataclasses import replace
from pathlib import Path
import math
import sys
from PySide6.QtCore import Qt, QSettings, QSignalBlocker
from PySide6.QtGui import QAction, QKeySequence, QFont, QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QComboBox, QCheckBox, QTabWidget, QSplitter, QFileDialog,
    QMessageBox, QDialog, QTextBrowser, QDialogButtonBox, QMenu, QSlider)
from .models import AppState, Quantity, MANUAL, WHITEPAPER
from .controller import Controller
from .controls import label, panel, scroll, NumberEdit, DistanceControl, MetricCard
from .theme import DARK, LIGHT, stylesheet
from .scene import GeometryView, export_geometry
from .preview import DetectorPreview
from .profile_editor import ProfileEditor
from .physics import angle_passes, required_crop, penumbra_um
from .projection import coverage, inspect_point, marker_points
from .solver import solve, hardware_violations
from .persistence import (save_plan, load_plan, save_profile, load_profile, atomic_text,
    export_parameters, parameter_csv, planning_summary)

RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def application_icon():
    pixmap = QPixmap(64, 64); pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(DARK['panel'])); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(1, 1, 62, 62, 13, 13)
    p.setPen(QColor(DARK['amber']))
    from PySide6.QtCore import QPointF
    for y in (13, 32, 51):
        p.drawLine(QPointF(12, 32), QPointF(51, y))
    p.setBrush(QColor(DARK['cyan'])); p.drawEllipse(25, 23, 15, 18)
    p.drawRect(50, 12, 3, 41); p.end()
    return QIcon(pixmap)


class StudioWindow(QMainWindow):
    def __init__(self, state=None, remember=True):
        super().__init__()
        self.setWindowTitle("Versa Geometry Studio")
        self.setWindowIcon(application_icon())
        self.resize(1600, 940)
        self.setMinimumSize(1080, 680)
        self.settings = QSettings("GeometryStudio", "VersaGeometryStudio") if remember else None
        self.controller = Controller(state, self)
        self.current_path = None
        self.candidate = None
        self.candidate_revision = None
        self.precision = int(self.settings.value("precision", 4)) if self.settings else 4
        self.precision = max(2, min(8, self.precision))
        self.theme_name = str(self.settings.value("theme", "dark")) if self.settings else "dark"
        self.req_edits, self.angle_edits, self.det_edits, self.ph_edits = {}, {}, {}, {}
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(16, 10, 16, 8); outer.setSpacing(10)
        self.build_header(outer)
        metrics = QHBoxLayout(); metrics.setSpacing(9)
        self.cards = {}
        for key, title in (("mg", "GEOMETRICAL MAGNIFICATION"), ("fov", "ACQUIRED CENTER-PLANE FOV"), ("sampling", "ACQUISITION SAMPLING"), ("D", "SOURCE → SCINTILLATOR"), ("angle", "SELECTED RAY ENVELOPE")):
            self.cards[key] = MetricCard(title); metrics.addWidget(self.cards[key])
        outer.addLayout(metrics)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel = self.build_left()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.build_center())
        self.splitter.addWidget(self.build_right())
        self.splitter.setStretchFactor(0, 0); self.splitter.setStretchFactor(1, 1); self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([275, 920, 320])
        outer.addWidget(self.splitter, 1)
        footer = QHBoxLayout()
        self.footer = label("", "muted")
        footer.addWidget(self.footer)
        footer.addStretch()
        footer.addWidget(label("OFFLINE  ·  PHYSICAL MODEL  ·  NO INSTRUMENT CONNECTION", "muted"))
        outer.addLayout(footer)
        self.build_menus()
        self.controller.changed.connect(self.sync)
        self.controller.preview_ready.connect(self.on_preview)
        self.controller.validation_failed.connect(self.show_error)
        self.controller.history_changed.connect(self.on_history)
        self.controller.sweep_ready.connect(self.on_sweep)
        self.apply_theme()
        self.sync(self.controller.state, self.controller.results, self.controller.revision)
        self.controller.request_preview(512)

    def build_header(self, outer):
        row = QHBoxLayout()
        mark = label("◈"); mark.setStyleSheet("font-size: 37px; color: #52dfd1; padding-right: 5px;")
        row.addWidget(mark)
        title = QVBoxLayout(); title.setSpacing(0)
        title.addWidget(label("VERSA GEOMETRY STUDIO", "title"))
        title.addWidget(label("TWO-STAGE X-RAY MICROSCOPY  /  PLAN · EXPLORE · EXPLAIN", "eyebrow"))
        row.addLayout(title); row.addStretch()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(("Explore geometry", "Plan acquisition", "Lock magnification", "Lock total separation"))
        self.mode_combo.setToolTip("One explicit mode at a time. The two locks are mutually exclusive. Planning requires Solve and Apply.")
        self.mode_combo.currentTextChanged.connect(lambda v: self.controller.set_state(replace(self.controller.state, mode=v)))
        row.addWidget(self.mode_combo)
        for text, fn in (("Open", self.open_plan), ("Save", self.save_current), ("Export ▾", self.show_export_menu)):
            btn = QPushButton(text); btn.clicked.connect(fn); row.addWidget(btn)
            if text.startswith("Export"):
                self.export_button = btn
        outer.addLayout(row)

    def build_left(self):
        box = panel(); box.setMinimumWidth(240); box.setMaximumWidth(410)
        layout = QVBoxLayout(box); layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(label("ACQUISITION WORKBENCH", "eyebrow"))
        self.profile_label = label("", "muted", True); layout.addWidget(self.profile_label)
        buttons = QHBoxLayout()
        editor = QPushButton("Edit profile"); editor.clicked.connect(self.edit_profile); buttons.addWidget(editor)
        restore = QPushButton("Reset demo"); restore.clicked.connect(self.controller.reset); buttons.addWidget(restore)
        layout.addLayout(buttons)
        tabs = QTabWidget(); self.left_tabs = tabs
        tabs.addTab(scroll(self.build_requirements()), "Plan")
        tabs.addTab(scroll(self.build_detector()), "Detector")
        tabs.addTab(scroll(self.build_phantom()), "Sample")
        layout.addWidget(tabs)
        self.candidate_label = label("Requirements are comparison targets until you solve and apply.", "muted", True)
        layout.addWidget(self.candidate_label)
        action_row = QHBoxLayout()
        action_row.addWidget(self.solve_button)
        action_row.addWidget(self.apply_button)
        layout.addLayout(action_row)
        return box

    def field(self, form, title, key, model, dest, callback, optional=False, integer=False):
        edit = NumberEdit(getattr(model, key), optional, integer)
        edit.committed.connect(lambda value, k=key: callback(k, value))
        form.addRow(title, edit)
        dest[key] = edit
        return edit

    def combo(self, form, title, options, callback):
        combo = QComboBox(); combo.addItems(options)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(4)
        combo.setMinimumWidth(70)
        combo.currentTextChanged.connect(callback)
        form.addRow(title, combo)
        return combo

    def build_requirements(self):
        w = QWidget(); layout = QVBoxLayout(w); layout.setContentsMargins(0, 8, 0, 0)
        st = self.controller.state
        layout.addWidget(label("IMAGING REQUIREMENTS", "eyebrow"))
        form = QFormLayout(); form.setHorizontalSpacing(7); form.setVerticalSpacing(8)
        self.field(form, "Sampling (µm/px)", "sampling_um", st.requirements, self.req_edits, self.change_req, True)
        self.sampling_mode = self.combo(form, "Sampling rule", ("exact", "no coarser"), lambda v: self.change_req("sampling_mode", v))
        self.field(form, "Min width (mm)", "fov_x_mm", st.requirements, self.req_edits, self.change_req, True)
        self.field(form, "Min height (mm)", "fov_y_mm", st.requirements, self.req_edits, self.change_req, True)
        self.field(form, "Margin / side (mm)", "margin_mm", st.requirements, self.req_edits, self.change_req)
        layout.addLayout(form)
        layout.addWidget(label("Blank sampling/FOV fields remove that requirement. Sampling is not measured resolution.", "muted", True))
        layout.addWidget(label("ANGLE CONSTRAINT", "eyebrow"))
        form = QFormLayout(); form.setVerticalSpacing(8)
        self.angle_axis = self.combo(form, "Envelope axis", ("diagonal", "horizontal", "vertical"), lambda v: self.change_angle("axis", v))
        self.angle_convention = self.combo(form, "Convention", ("full", "half"), lambda v: self.change_angle("convention", v))
        self.field(form, "Limit (degrees)", "limit_deg", st.angle, self.angle_edits, self.change_angle, True)
        self.field(form, "Buffer (degrees)", "buffer_deg", st.angle, self.angle_edits, self.change_angle)
        self.angle_envelope = self.combo(form, "Evaluate", ("active", "crop"), lambda v: self.change_angle("envelope", v))
        self.strict_check = QCheckBox("Strictly below the angle limit")
        self.strict_check.toggled.connect(lambda v: self.change_angle("strict", v)); form.addRow(self.strict_check)
        layout.addLayout(form)
        layout.addWidget(label("PAIR SELECTION", "eyebrow"))
        form = QFormLayout()
        self.fixed_kind = self.combo(form, "Fix a distance", ("none", "a", "b", "D"), self.change_fixed_kind)
        self.field(form, "Fixed value (mm)", "fixed_mm", st.requirements, self.req_edits, self.change_req, True)
        self.goal = self.combo(form, "Solver goal", ("minimum separation", "closest to current distances"), lambda v: self.change_req("goal", v))
        layout.addLayout(form)
        self.solve_button = QPushButton("Solve")
        self.solve_button.setObjectName("primary"); self.solve_button.clicked.connect(self.solve_plan)
        self.solve_button.setToolTip("Solve acquisition requirements and review a concrete distance pair")
        self.apply_button = QPushButton("Apply to scene"); self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_candidate)
        self.solver_text = label("Solve chooses a distance pair explicitly. Requirements stay separate from the explored geometry.", "muted", True)
        self.solver_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.solver_text)
        layout.addWidget(label("Ties: exact locks → minimum D → finest sampling with coverage → closest current pair.", "muted", True))
        layout.addStretch()
        return w

    def build_detector(self):
        w = QWidget(); layout = QVBoxLayout(w); layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(label("CAMERA & OPTICAL CALIBRATION", "eyebrow"))
        form = QFormLayout(); form.setVerticalSpacing(9)
        self.objective_combo = self.combo(form, "Objective", tuple(self.controller.state.profile.objectives), self.change_objective)
        d = self.controller.state.profile.detector
        for title, key, optional, integer in (("Native columns (px)", "nx", False, True), ("Native rows (px)", "ny", False, True),
            ("Chip pitch (µm)", "pitch_um", False, False), ("Optical scale (×)", "optical_m", False, False),
            ("Usable columns (px)", "usable_nx", True, True), ("Usable rows (px)", "usable_ny", True, True),
            ("Image circle (mm)", "image_circle_mm", True, False)):
            self.field(form, title, key, d, self.det_edits, self.change_detector, optional, integer)
        self.binning_combo = self.combo(form, "Binning", ("1", "2", "4", "8"), lambda v: self.change_detector("binning", int(v)))
        self.field(form, "Crop columns (out px)", "crop_nx", d, self.det_edits, self.change_detector, True, True)
        self.field(form, "Crop rows (out px)", "crop_ny", d, self.det_edits, self.change_detector, True, True)
        layout.addLayout(form)
        for key, title in (("flip_y", "Flip optical horizontal parity"), ("flip_z", "Flip optical vertical parity")):
            check = QCheckBox(title)
            check.toggled.connect(lambda v, k=key: self.change_detector(k, v))
            setattr(self, key+"_check", check); layout.addWidget(check)
        self.detector_detail = label("", "muted", True); layout.addWidget(self.detector_detail)
        crop = QPushButton("Suggest integer crop for requirements")
        crop.clicked.connect(self.suggest_crop); layout.addWidget(crop)
        layout.addWidget(label("Blank usable area = full native chip. A configured image circle limits a centered inscribed rectangle. Crop is in acquired binned pixels. Binning preserves full usable field.", "muted", True))
        layout.addStretch()
        return w

    def build_phantom(self):
        w = QWidget(); layout = QVBoxLayout(w); layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(label("FINITE SPECIMEN", "eyebrow"))
        form = QFormLayout(); form.setVerticalSpacing(8)
        self.shape_combo = self.combo(form, "Phantom", ("cuboid", "ellipsoid"), lambda v: self.change_phantom("shape", v))
        ph = self.controller.state.phantom
        for title, key in (("Width y (mm)", "width_mm"), ("Height z (mm)", "height_mm"), ("Depth x (mm)", "depth_mm"),
            ("Offset x (mm)", "offset_x_mm"), ("Offset y (mm)", "offset_y_mm"), ("Offset z (mm)", "offset_z_mm"),
            ("Rotation (degrees)", "rotation_deg"), ("Host μ (mm⁻¹)", "mu_mm_inv"), ("Inclusion μ (mm⁻¹)", "inclusion_mu_mm_inv")):
            self.field(form, title, key, ph, self.ph_edits, self.change_phantom)
        layout.addLayout(form)
        self.roi_check = QCheckBox("Plan an interior target ROI")
        self.roi_check.toggled.connect(lambda v: self.change_phantom("roi_enabled", v)); layout.addWidget(self.roi_check)
        form = QFormLayout()
        for title, key in (("ROI width (mm)", "roi_width_mm"), ("ROI height (mm)", "roi_height_mm"), ("ROI depth (mm)", "roi_depth_mm"),
            ("ROI offset x (mm)", "roi_offset_x_mm"), ("ROI offset y (mm)", "roi_offset_y_mm"), ("ROI offset z (mm)", "roi_offset_z_mm")):
            self.field(form, title, key, ph, self.ph_edits, self.change_phantom)
        layout.addLayout(form)
        self.sweep_increment = NumberEdit(5.0); form = QFormLayout(); form.addRow("Sweep step (degrees)", self.sweep_increment); layout.addLayout(form)
        self.sweep_button = QPushButton("Assess 0–360° coverage")
        self.sweep_button.clicked.connect(self.start_sweep); layout.addWidget(self.sweep_button)
        self.sweep_text = label("Sampled sweep; exact per-angle extents, with local angular refinement. No continuous-angle guarantee.", "muted", True)
        layout.addWidget(self.sweep_text)
        layout.addWidget(label("Synthetic geometry/attenuation demonstration. Illustrative coefficients; no spectrum or detector-response calibration.", "muted", True))
        layout.addStretch()
        return w

    def build_center(self):
        box = panel(); box.setMinimumWidth(440)
        layout = QVBoxLayout(box); layout.setContentsMargins(4, 10, 4, 7); layout.setSpacing(3)
        toolbar = QHBoxLayout(); toolbar.setContentsMargins(10, 0, 10, 0)
        toolbar.addWidget(label("PHYSICAL RAY GEOMETRY", "eyebrow")); toolbar.addStretch()
        for text, fn in (("Controls", self.toggle_controls), ("Fit views", self.fit_views), ("Equations", self.show_equations)):
            btn = QPushButton(text); btn.clicked.connect(fn); toolbar.addWidget(btn)
        layout.addLayout(toolbar)
        self.mode_hint = label("", "muted", True); self.mode_hint.setContentsMargins(12, 2, 12, 0); layout.addWidget(self.mode_hint)
        self.top_view, self.side_view = GeometryView("top"), GeometryView("side")
        for view in (self.top_view, self.side_view):
            view.distance_moved.connect(self.controller.move_distance)
            view.drag_started.connect(self.controller.begin_transaction)
            view.drag_finished.connect(self.controller.end_transaction)
            view.marker_selected.connect(self.select_marker)
        view_split = QSplitter(Qt.Orientation.Vertical)
        view_split.addWidget(self.top_view); view_split.addWidget(self.side_view)
        view_split.setSizes([300, 240]); layout.addWidget(view_split, 1)
        controls = QHBoxLayout(); controls.setSpacing(15)
        self.source_control = DistanceControl("a", "SOURCE → CENTER · a", self.controller.state.geometry.a_mm)
        self.detector_control = DistanceControl("b", "CENTER → SCINTILLATOR · b", self.controller.state.geometry.b_mm)
        for control in (self.source_control, self.detector_control):
            control.moved.connect(self.controller.move_distance)
            control.drag_started.connect(self.controller.begin_transaction)
            control.drag_finished.connect(self.controller.end_transaction)
            controls.addWidget(control)
        layout.addLayout(controls)
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal); self.rotation_slider.setRange(0, 3600)
        self.rotation_slider.setToolTip("Specimen rotation around physical z; 0.1° steps")
        self.rotation_slider.sliderPressed.connect(self.controller.begin_transaction)
        self.rotation_slider.sliderReleased.connect(self.controller.end_transaction)
        self.rotation_slider.valueChanged.connect(lambda v: self.change_phantom("rotation_deg", v/10))
        rotation_row = QHBoxLayout(); rotation_row.setContentsMargins(12, 0, 12, 0)
        rotation_row.addWidget(label("ROTATION", "muted")); rotation_row.addWidget(self.rotation_slider, 1)
        self.rotation_label = label("0.0°", "muted"); rotation_row.addWidget(self.rotation_label)
        layout.addLayout(rotation_row)
        legend = label("● X-rays  ·  ● FOV / ROI  ·  ● visible light relay     |     Sliders explore the model; hardware travel is unconfigured.", "muted", True)
        legend.setContentsMargins(12, 4, 12, 0); layout.addWidget(legend)
        return box

    def build_right(self):
        box = panel(); box.setMinimumWidth(265); box.setMaximumWidth(440)
        layout = QVBoxLayout(box); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(6)
        row = QHBoxLayout(); row.addWidget(label("DETECTOR PROJECTION", "eyebrow")); row.addStretch()
        self.grid_check = QCheckBox("Grid"); self.grid_check.setToolTip("Display grid, decimated to at most 64 divisions; acquired pixel count is unchanged")
        self.grid_check.toggled.connect(self.toggle_grid); row.addWidget(self.grid_check); layout.addLayout(row)
        self.preview = DetectorPreview()
        self.preview.hovered.connect(self.preview_hover)
        self.preview.cursor_info.connect(lambda text: self.inspector_label.setText(text))
        self.preview.marker_selected.connect(self.select_marker)
        layout.addWidget(self.preview, 3)
        layout.addWidget(label("Synthetic geometry / attenuation demonstration", "muted", True))
        self.render_label = label("", "muted"); layout.addWidget(self.render_label)
        details = QWidget(); detail_layout = QVBoxLayout(details); detail_layout.setContentsMargins(0, 8, 0, 0); detail_layout.setSpacing(8)
        detail_layout.addWidget(label("LIVE FEASIBILITY", "eyebrow"))
        self.status_label = label("", None, True); detail_layout.addWidget(self.status_label)
        detail_layout.addWidget(label("ANGLE READOUT · FULL / HALF", "eyebrow"))
        self.angle_label = label("", None, True); detail_layout.addWidget(self.angle_label)
        self.coverage_label = label("", "muted", True); detail_layout.addWidget(self.coverage_label)
        detail_layout.addWidget(label("POINT / RAY INSPECTOR", "eyebrow"))
        self.inspector_label = label("", "muted", True); self.inspector_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); detail_layout.addWidget(self.inspector_label)
        detail_layout.addWidget(label("HARDWARE & CALIBRATION", "eyebrow"))
        self.hardware_label = label("", "muted", True); detail_layout.addWidget(self.hardware_label)
        self.error_label = label("", None, True); detail_layout.addWidget(self.error_label)
        detail_layout.addStretch()
        layout.addWidget(scroll(details), 4)
        return box

    def build_menus(self):
        file_menu = self.menuBar().addMenu("File")
        def action(menu, text, fn, shortcut=None):
            a = QAction(text, self); a.triggered.connect(fn)
            if shortcut:
                a.setShortcut(shortcut)
            menu.addAction(a)
            return a
        action(file_menu, "Open acquisition plan…", self.open_plan, QKeySequence.StandardKey.Open)
        action(file_menu, "Save acquisition plan…", self.save_current, QKeySequence.StandardKey.Save)
        action(file_menu, "Save plan as…", lambda: self.save_current(True), QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        action(file_menu, "Import instrument profile…", self.import_profile)
        action(file_menu, "Export instrument profile…", self.export_profile)
        action(file_menu, "Restore default demo", self.controller.reset)
        file_menu.addSeparator(); action(file_menu, "Exit", self.close)
        edit_menu = self.menuBar().addMenu("Edit")
        self.undo_action = action(edit_menu, "Undo", self.controller.undo, QKeySequence.StandardKey.Undo)
        self.redo_action = action(edit_menu, "Redo", self.controller.redo, QKeySequence.StandardKey.Redo)
        self.undo_action.setEnabled(False); self.redo_action.setEnabled(False)
        action(edit_menu, "Copy parameter table", self.copy_parameters, "Ctrl+Shift+C")
        action(edit_menu, "Instrument profile…", self.edit_profile)
        view = self.menuBar().addMenu("View")
        action(view, "Toggle light / dark theme", self.toggle_theme)
        action(view, "Fit geometry", self.fit_views, "F")
        self.corner_action = action(view, "Show specimen vertex rays", self.toggle_corner_rays)
        self.corner_action.setCheckable(True)
        precision = view.addMenu("Display precision")
        for n in (2, 4, 6, 8):
            action(precision, f"{n} decimal places", lambda checked=False, v=n: self.set_precision(v))
        help_menu = self.menuBar().addMenu("Help")
        action(help_menu, "How this is calculated", self.show_equations)
        self.export_menu = QMenu(self)
        for text, fn in (("Geometry PNG / SVG…", self.export_scene), ("Detector image (annotated)…", lambda: self.export_preview(True)),
            ("Detector image (raw)…", lambda: self.export_preview(False)), ("Parameter CSV / JSON…", self.export_table),
            ("Planning summary Markdown…", self.export_summary)):
            action(self.export_menu, text, fn)

    def change_req(self, key, value):
        st = self.controller.state
        self.controller.set_state(replace(st, requirements=replace(st.requirements, **{key: value})))

    def change_fixed_kind(self, value):
        st = self.controller.state
        fixed = st.requirements.fixed_mm
        if value != "none" and fixed is None:
            fixed = {"a": st.geometry.a_mm, "b": st.geometry.b_mm, "D": self.controller.results.D_mm}[value]
        self.controller.set_state(replace(st, requirements=replace(st.requirements, fixed_kind=value, fixed_mm=fixed)))

    def change_angle(self, key, value):
        st = self.controller.state
        self.controller.set_state(replace(st, angle=replace(st.angle, **{key: value})))

    def change_detector(self, key, value):
        st, profile = self.controller.state, self.controller.state.profile
        detector = profile.detector
        provenance = dict(detector.provenance)
        unit = "µm" if key == "pitch_um" else "×" if key == "optical_m" else "mm" if key == "image_circle_mm" else "pixels" if key.endswith(("nx", "ny")) else "dimensionless"
        if not isinstance(value, bool):
            provenance[key] = Quantity(value, unit, "user supplied", False)
        updated = replace(detector, **{key: value}, provenance=provenance)
        if self.controller.set_state(replace(st, profile=profile.with_detector(updated))):
            self.error_label.clear()

    def change_objective(self, value):
        st = self.controller.state
        if value in st.profile.objectives:
            self.controller.set_state(replace(st, profile=replace(st.profile, selected_objective=value)))

    def change_phantom(self, key, value):
        st = self.controller.state
        self.controller.set_state(replace(st, phantom=replace(st.phantom, **{key: value})))

    def sync(self, state, r, revision):
        precision = self.precision
        fmt = lambda value: f"{value:.{precision}f}"
        self.error_label.clear()
        self.cards['mg'].update_value(fmt(r.geometrical_m)+"×", f"optical × geometry = {r.total_m:.5g}×", repr(r.geometrical_m))
        self.cards['fov'].update_value(f"{r.crop_fov_x_mm:.3f} × {r.crop_fov_y_mm:.3f}", "mm · centered acquisition crop", f"{r.crop_fov_x_mm!r} × {r.crop_fov_y_mm!r} mm")
        self.cards['sampling'].update_value(fmt(r.sampling_um), f"µm / acquired pixel · {r.crop_nx} × {r.crop_ny} px", repr(r.sampling_um))
        self.cards['D'].update_value(fmt(r.D_mm)+" mm", f"a {r.a_mm:.3f} · b {r.b_mm:.3f} mm", f"a={r.a_mm!r} mm; b={r.b_mm!r} mm; D={r.D_mm!r} mm")
        selected = r.selected_angle_deg(state.angle)
        self.cards['angle'].update_value(fmt(selected)+"°", f"{state.angle.convention} {state.angle.axis} · {state.angle.envelope}", repr(selected))
        self.profile_label.setText(state.profile.selected_objective+" objective · "+state.profile.objectives[state.profile.selected_objective].availability+"\n"+state.profile.name)
        self.profile_label.setToolTip(state.profile.notes)
        combos = ((self.mode_combo, state.mode), (self.sampling_mode, state.requirements.sampling_mode), (self.fixed_kind, state.requirements.fixed_kind),
            (self.goal, state.requirements.goal), (self.angle_axis, state.angle.axis), (self.angle_convention, state.angle.convention),
            (self.angle_envelope, state.angle.envelope), (self.binning_combo, str(state.profile.detector.binning)), (self.shape_combo, state.phantom.shape))
        with QSignalBlocker(self.objective_combo):
            self.objective_combo.clear(); self.objective_combo.addItems(tuple(state.profile.objectives)); self.objective_combo.setCurrentText(state.profile.selected_objective)
        for combo, value in combos:
            with QSignalBlocker(combo):
                combo.setCurrentText(value)
        for edits, model in ((self.req_edits, state.requirements), (self.angle_edits, state.angle), (self.det_edits, state.profile.detector), (self.ph_edits, state.phantom)):
            for key, edit in edits.items():
                if not (edit.hasFocus() and edit.isModified()):
                    edit.set_value(getattr(model, key))
        for check, value in ((self.strict_check, state.angle.strict), (self.roi_check, state.phantom.roi_enabled),
            (self.flip_y_check, state.profile.detector.flip_y), (self.flip_z_check, state.profile.detector.flip_z)):
            with QSignalBlocker(check):
                check.setChecked(value)
        self.req_edits['fixed_mm'].setEnabled(state.requirements.fixed_kind != "none")
        self.source_control.set_value(r.a_mm); self.detector_control.set_value(r.b_mm)
        planned = state.mode == "Plan acquisition"
        self.source_control.setEnabled(not planned); self.detector_control.setEnabled(not planned)
        self.top_view.setEnabled(not planned); self.side_view.setEnabled(not planned)
        self.mode_hint.setText({"Explore geometry": "a and b are independent · requirements remain comparison targets · drag hardware to explore",
            "Plan acquisition": "Requirements are inputs · Solve creates a candidate · Apply updates the physical scene",
            "Lock magnification": f"M_g locked at {r.geometrical_m:.9g}× · a / b linked · FOV and sampling stay constant",
            "Lock total separation": f"D locked at {r.D_mm:.9g} mm · a / b linked · magnification changes"}[state.mode])
        self.top_view.set_state(state, r); self.side_view.set_state(state, r)
        self.preview.set_state(state, r, revision)
        self.render_label.setText("Projection updating · revision "+str(revision))
        with QSignalBlocker(self.rotation_slider):
            self.rotation_slider.setValue(round(state.phantom.rotation_deg % 360 * 10))
        self.rotation_label.setText(f"{state.phantom.rotation_deg:.1f}°")
        self.detector_detail.setText(f"Native chip {r.camera_x_mm:.5g} × {r.camera_y_mm:.5g} mm\nUsable scintillator {r.scintillator_x_mm:.5g} × {r.scintillator_y_mm:.5g} mm\nUsable output {r.output_nx} × {r.output_ny} px\nAcquired crop {r.crop_nx} × {r.crop_ny} px")
        self.update_status(state, r)
        self.select_marker(self.preview.selected_marker)
        self.apply_button.setEnabled(self.candidate is not None and self.candidate_revision == revision)
        if self.candidate_revision is not None and self.candidate_revision != revision:
            self.candidate_label.setText("Setup changed. Solve again to review a current candidate.")
        self.sweep_text.setText("Run assessment for current setup. Sampled angles with local refinement; no continuous-angle guarantee.")
        self.footer.setText(f"Revision {revision} · model exploration · {state.mode}")

    def update_status(self, st, r):
        req = st.requirements
        statuses = []
        lengths = (None if req.fov_x_mm is None else req.fov_x_mm+2*req.margin_mm,
                   None if req.fov_y_mm is None else req.fov_y_mm+2*req.margin_mm)
        fov_ok = all(target is None or actual >= target-1e-8 for target, actual in zip(lengths, (r.crop_fov_x_mm, r.crop_fov_y_mm)))
        statuses.append((fov_ok, "Coverage requirement met" if fov_ok else f"Coverage shortfall: field {r.crop_fov_x_mm:.4g} × {r.crop_fov_y_mm:.4g} mm"))
        if req.sampling_um:
            sample_ok = math.isclose(r.sampling_um, req.sampling_um, rel_tol=1e-9) if req.sampling_mode == "exact" else r.sampling_um <= req.sampling_um+1e-9
            statuses.append((sample_ok, "Sampling requirement met" if sample_ok else f"Sampling {r.sampling_um:.5g} vs target {req.sampling_um:.5g} µm/px ({req.sampling_mode})"))
        if st.angle.limit_deg is not None:
            ok = angle_passes(r, st.angle)
            statuses.append((ok, f"Selected angle {'below' if st.angle.strict else 'within'} {st.angle.limit_deg:g}° limit" if ok else f"Selected angle exceeds/equal limit by {r.selected_angle_deg(st.angle)-st.angle.limit_deg:.4g}°"))
        self.status_label.setText("\n".join(("✓ " if passed else "! ")+text for passed, text in statuses))
        self.status_label.setStyleSheet(f"color: {self.colors['text']}; line-height: 1.5;")
        for axis, length, available in zip(("width", "height"), lengths, (r.crop_nx, r.crop_ny)):
            if length and req.sampling_um:
                needed, achieved = required_crop(length, req.sampling_um)
                if needed > available:
                    self.status_label.setText(self.status_label.text()+f"\n! {length:g} mm {axis} at {req.sampling_um:g} µm needs {needed} pixels; {available} available.")
        vals = r.half_angles_rad if st.angle.envelope == "active" else r.crop_half_angles_rad
        self.angle_label.setText("\n".join(f"{axis:<10}  {2*math.degrees(v):.6f}° / {math.degrees(v):.6f}°" for axis, v in zip(("Horizontal", "Vertical", "Diagonal"), vals)))
        cov = coverage(st.geometry, st.profile.detector, st.phantom)
        text = f"Specimen: {'TRUNCATED at this angle' if cov['clipped'] else 'covered at this angle'}\nProjected extent / M_g: {cov['equivalent_center_extent_mm'][0]:.3f} × {cov['equivalent_center_extent_mm'][1]:.3f} mm."
        if st.phantom.roi_enabled:
            roi = coverage(st.geometry, st.profile.detector, st.phantom, True)
            text += f"\nTarget ROI: {'clipped' if roi['clipped'] else 'covered'} (independent of outer truncation)."
        text += "\nCenter-plane FOV and full-rotation coverage are different."
        self.coverage_label.setText(text)
        violations = hardware_violations(st)
        configured = sum(q.value is not None and q.confirmed for q in st.profile.bounds.values())
        legacy = st.profile.legacy_stage_min
        legacy_value = "unconfigured" if legacy.value is None else f"{legacy.value:g} mm"
        hardware = f"{configured} confirmed profile bounds. Travel / clearances with blank values: UNCONFIGURED.\nLegacy stage minimum: {legacy_value}, {'confirmed' if legacy.confirmed else 'unconfirmed'}; mapping {'verified' if st.profile.mapping.verified else 'unconfigured'}."
        if violations:
            hardware += "\n! " + "\n! ".join(violations)
        focal = st.profile.focal_spot_um.value
        if focal:
            hardware += f"\nApproximate object penumbra {penumbra_um(focal, r.geometrical_m):.5g} µm; not true resolution."
        self.hardware_label.setText(hardware)

    def on_preview(self, result):
        self.preview.set_render(result)
        if result.revision == self.controller.revision:
            self.render_label.setText(f"{result.transmission.shape[1]} × {result.transmission.shape[0]} display · {result.elapsed_ms:.1f} ms render · deterministic")

    def select_marker(self, index):
        self.preview.selected_marker = index
        for view in (self.top_view, self.side_view):
            view.item.selected_marker = index; view.item.update()
        st = self.controller.state
        point = marker_points(st.phantom)[index]
        info = inspect_point(point, st.geometry, st.profile.detector)
        self.inspector_label.setText(f"Inclusion {chr(65+index)} · P=({point[0]:.3f}, {point[1]:.3f}, {point[2]:.3f}) mm\nPerspective M={info.magnification:.6f}×\nScintillator y,z=({info.scintillator_mm[1]:.3f}, {info.scintillator_mm[2]:.3f}) mm\nCamera u,v=({info.pixel_uv[0]:.2f}, {info.pixel_uv[1]:.2f}) px\n{'Clipped by crop' if info.clipped_crop else 'Inside acquired field'} · hover detector to inspect a ray")
        self.preview.update()

    def preview_hover(self, yz):
        for view in (self.top_view, self.side_view):
            view.item.hover_yz = yz; view.item.update()
        if yz is None:
            self.select_marker(self.preview.selected_marker)

    def solve_plan(self):
        try:
            result = solve(self.controller.state)
            self.candidate = result.candidate
            self.candidate_revision = self.controller.revision
            self.solver_text.setText(result.status.upper()+"\n"+result.explanation)
            if result.candidate:
                g = result.candidate
                self.candidate_label.setText(f"CANDIDATE · a {g.a_mm:.6f} mm\nb {g.b_mm:.6f} mm · D {g.a_mm+g.b_mm:.6f} mm\n{self.controller.state.requirements.goal}")
                self.candidate_label.setToolTip(result.explanation)
            else:
                text = result.explanation
                if "needs " in text:
                    text = text[text.index("Requested "):text.index(" available.")+11]
                elif len(text)>200:
                    text=text[:197]+"…"
                self.candidate_label.setText(result.status.upper()+" · "+text)
                self.candidate_label.setToolTip(result.explanation)
            if result.candidate and any(v is not None for v in result.required_crop_pixels):
                self.solver_text.setText(self.solver_text.text()+f"\nRequired integer crop: {result.required_crop_pixels} pixels; achieved coverage {result.achieved_coverage_mm} mm (rounded upward).")
            self.apply_button.setEnabled(result.candidate is not None)
        except (ValueError, TypeError) as exc:
            self.show_error(str(exc))

    def apply_candidate(self):
        if self.candidate and self.candidate_revision == self.controller.revision:
            self.controller.set_state(replace(self.controller.state, geometry=self.candidate))

    def suggest_crop(self):
        st, r = self.controller.state, self.controller.results
        lengths = (st.requirements.fov_x_mm, st.requirements.fov_y_mm)
        counts, achieved = [], []
        for length, fallback in zip(lengths, (r.crop_nx, r.crop_ny)):
            c, a = required_crop(length+2*st.requirements.margin_mm, r.sampling_um) if length else (fallback, fallback*r.sampling_um/1000)
            counts.append(c); achieved.append(a)
        d = replace(st.profile.detector, crop_nx=counts[0], crop_ny=counts[1])
        if self.controller.set_state(replace(st, profile=st.profile.with_detector(d))):
            self.detector_detail.setText(self.detector_detail.text()+f"\nRounded-up crop achieves {achieved[0]:.9g} × {achieved[1]:.9g} mm.")

    def start_sweep(self):
        try:
            increment = self.sweep_increment.parsed()
            if not 0 < increment <= 90:
                raise ValueError("Sweep increment must be greater than 0 and at most 90 degrees")
            if self.controller.request_sweep(increment):
                self.sweep_button.setEnabled(False)
                self.sweep_text.setText("Assessing rotation in a worker…")
        except ValueError as exc:
            self.show_error(str(exc))

    def on_sweep(self, result):
        self.sweep_button.setEnabled(True)
        if result.get("stale"):
            self.sweep_text.setText("Setup changed during sweep; rerun for current revision.")
        elif "error" in result:
            self.sweep_text.setText(result['error'])
        else:
            ext = result['max_equivalent_center_extent_mm']
            self.sweep_text.setText(f"SAMPLED assessment: {result['samples']} views at {result['increment_deg']:g}°; local refinement {result['local_refinement_deg']:g}°.\nWorst angle {result['worst_angle_deg']:.3f}°. Max extent / M_g {ext[0]:.4f} × {ext[1]:.4f} mm.\nOuter specimen {'truncated' if result['specimen_clipped'] else 'covered'}; ROI {result['roi_clipped']}.\nNot a continuous-angle guarantee.")

    def edit_profile(self):
        dialog = ProfileEditor(self.controller.state.profile, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.controller.set_state(replace(self.controller.state, profile=dialog.result_profile))

    def open_plan(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open acquisition plan", str(self.current_path or RESOURCE_ROOT/"examples"), "Acquisition plans (*.json)")
        if not path:
            return
        try:
            state, warnings = load_plan(path)
            if self.controller.set_state(state):
                self.current_path = Path(path)
                if warnings:
                    QMessageBox.information(self, "Plan recomputed", "\n".join(warnings))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Cannot open plan", str(exc))

    def save_current(self, save_as=False):
        path = str(self.current_path) if self.current_path and not save_as else ""
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save acquisition plan", str(self.current_path or Path.cwd()/"acquisition-plan.json"), "Acquisition plan (*.json)")
        if path:
            try:
                save_plan(path, self.controller.state); self.current_path = Path(path)
                self.statusBar().showMessage("Saved full-precision acquisition plan", 4000)
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import instrument profile", str(RESOURCE_ROOT/"profiles"), "Instrument profiles (*.json)")
        if path:
            try:
                profile = load_profile(path)
                self.controller.set_state(replace(self.controller.state, profile=profile))
                if self.settings:
                    self.settings.setValue("last_profile", path)
            except (OSError, ValueError, TypeError) as exc:
                QMessageBox.warning(self, "Cannot load profile", str(exc))

    def export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export instrument profile", "instrument-profile.json", "Instrument profile (*.json)")
        if path:
            try:
                save_profile(path, self.controller.state.profile)
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def show_export_menu(self):
        self.export_menu.exec(self.export_button.mapToGlobal(self.export_button.rect().bottomLeft()))

    def export_scene(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export geometry", "versa-geometry.svg", "SVG vector (*.svg);;PNG image (*.png)")
        if path:
            try:
                export_geometry(path, (self.top_view, self.side_view))
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def export_preview(self, annotated=True):
        path, _ = QFileDialog.getSaveFileName(self, "Export synthetic projection", "synthetic-projection.png", "PNG image (*.png)")
        if path:
            try:
                if self.preview.image_revision != self.controller.revision:
                    raise ValueError("Wait for the current projection to finish")
                self.preview.export_image(path, annotated)
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def export_table(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export parameters", "versa-parameters.csv", "CSV table (*.csv);;JSON table (*.json)")
        if path:
            try:
                export_parameters(path, self.controller.state)
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def export_summary(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export planning summary", "versa-plan.md", "Markdown (*.md)")
        if path:
            try:
                atomic_text(path, planning_summary(self.controller.state))
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))

    def copy_parameters(self):
        QApplication.clipboard().setText(parameter_csv(self.controller.state, "\t"))
        self.statusBar().showMessage("Parameter table copied with units", 3000)

    def show_equations(self):
        dialog = QDialog(self); dialog.setWindowTitle("How this is calculated"); dialog.resize(780, 620)
        layout = QVBoxLayout(dialog); browser = QTextBrowser(); browser.setOpenExternalLinks(True)
        browser.setHtml(f"""<h2>Two magnifications. One physical coordinate system.</h2>
        <p>The source is (−a, 0, 0); rotation center is (0, 0, 0); scintillator is x=b. All geometry is mm.</p>
        <h3>Camera → scintillator → object</h3><p>M<sub>g</sub> = (a+b)/a; M<sub>total</sub> = m M<sub>g</sub>.<br>
        W = N<sub>usable</sub> p/m; Δ = k p/(m M<sub>g</sub>); FOV = N<sub>out</sub> Δ.<br>
        Camera pitch p is converted from µm to mm. Binning changes Δ and pixel count; full usable FOV is unchanged.</p>
        <h3>Angular envelope</h3><p>α = atan(R/D); θ = 2α. R = W<sub>x</sub>/2, W<sub>y</sub>/2, or √(W<sub>x</sub>²+W<sub>y</sub>²)/2.<br>
        D<sub>equality</sub> = R/tan(α<sub>limit</sub>). Buffer is subtracted in your chosen full/half convention first.
        Equality is excluded by a strict limit. Trigonometry uses radians. Numerical angle tolerance: 10<sup>−9</sup> degrees.</p>
        <h3>Planning</h3><p>Imaging magnification ratios and confirmed physical bounds form linear inequalities in (a,b).
        Intersections determine the minimum-D solution exactly. Orthogonal boundary projections provide closest-distance candidates.
        Feasibility tolerance: 10<sup>−7</sup> mm. No exploration slider limit is used as hardware data.
        Ties preserve exact locks, then favor minimum separation, finest permitted sampling, and proximity to the current pair.</p>
        <h3>Perspective and transmission</h3><p>t = (a+b)/(a+x); projected point = (b, t y, t z); a+x must be positive.<br>
        Pixel centers: u = y<sub>camera</sub>/(k p) + (N<sub>out</sub>−1)/2; physical edges clip rays.
        Display rows point downward; physical z and v point upward; optical parity is configurable.<br>
        I/I₀ = exp[−μ<sub>host</sub> ℓ<sub>host</sub> − (μ<sub>inclusion</sub>−μ<sub>host</sub>) ℓ<sub>inclusion</sub>].
        Cuboid slab and ellipsoid quadratic intersections use finite source-to-scintillator segments.</p>
        <h3>Calibration</h3><p>Acquired sampling is not true spatial resolution. Synthetic coefficients are illustrative.
        Lens relay spacing and hardware artwork are schematic. Source emission cone, travel and unknown clearances remain unconfigured.
        The 135 mm legacy Source Z / Detector Z rule stays in stage coordinates until a signed mapping is verified and the reference confirmed.</p>
        <p><a href='{WHITEPAPER}'>ZEISS two-stage architecture</a> · <a href='{MANUAL}'>Legacy ZEISS guide v11.x</a> ·
        <a href='https://doc.qt.io/qt-6.11/supported-platforms.html'>Qt 6.11 platform requirements</a></p>""")
        layout.addWidget(browser); buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject); layout.addWidget(buttons); dialog.exec()

    def toggle_controls(self):
        self.left_panel.setVisible(not self.left_panel.isVisible())

    def fit_views(self):
        self.top_view.fit(); self.side_view.fit()

    def toggle_corner_rays(self, checked):
        for view in (self.top_view, self.side_view):
            view.item.corner_rays = checked; view.item.update()

    def toggle_grid(self, checked):
        self.preview.grid = checked; self.preview.update()

    def apply_theme(self):
        self.colors = LIGHT if self.theme_name == "light" else DARK
        self.setStyleSheet(stylesheet(self.colors))
        for view in (self.top_view, self.side_view):
            view.set_theme(self.colors)
        self.preview.colors = self.colors; self.preview.update()

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.apply_theme(); self.update_status(self.controller.state, self.controller.results)

    def set_precision(self, value):
        self.precision = value
        self.sync(self.controller.state, self.controller.results, self.controller.revision)
        self.controller.request_preview(512)

    def show_error(self, text):
        self.error_label.setText("Input retained at last valid state: "+text)
        self.error_label.setStyleSheet(f"color: {self.colors['red']};")
        self.statusBar().showMessage(text, 7000)

    def on_history(self, undo, redo):
        self.undo_action.setEnabled(undo); self.redo_action.setEnabled(redo)

    def closeEvent(self, event):
        if self.settings:
            self.settings.setValue("theme", self.theme_name)
            self.settings.setValue("precision", self.precision)
        self.controller.shutdown()
        super().closeEvent(event)
