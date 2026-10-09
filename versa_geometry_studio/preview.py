"""Linked detector front view. Physical z-up is separate from display row-down."""
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QFont
from PySide6.QtWidgets import QWidget
from .projection import marker_points, inspect_point, phantom_points, project_points, ray_path_lengths
from .scene import pen, polygon, hull
from .theme import DARK


class DetectorPreview(QWidget):
    hovered = Signal(object)
    cursor_info = Signal(str)
    marker_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.state = self.results = None
        self.revision = -1
        self.image_revision = -2
        self.image = None
        self.render_ms = 0
        self.colors = DARK
        self.grid = False
        self.annotations = True
        self.selected_marker = 0
        self.cursor_pos = None
        self.setMinimumSize(180, 180)
        self.setMouseTracking(True)

    def set_state(self, state, results, revision):
        self.state, self.results, self.revision = state, results, revision
        self.update()

    def set_render(self, result):
        if result.revision != self.revision:
            return
        intensity = np.clip(result.transmission*255, 0, 255).astype(np.uint8)
        image = QImage(intensity.data, intensity.shape[1], intensity.shape[0], intensity.strides[0], QImage.Format.Format_Grayscale8)
        self.image = image.copy()
        self.image_revision = result.revision
        self.render_ms = result.elapsed_ms
        self.update()

    def image_rect(self):
        if self.results is None:
            return QRectF()
        r = self.results
        width, height = self.width()-36, self.height()-46
        ratio = r.scintillator_x_mm/r.scintillator_y_mm
        w, h = min(width, height*ratio), min(height, width/ratio)
        return QRectF((self.width()-w)/2, 8, w, h)

    def map_yz(self, yz):
        r, box, d = self.results, self.image_rect(), self.state.profile.detector
        y, z = yz
        if d.flip_y:
            y = -y
        if d.flip_z:
            z = -z
        return QPointF(box.center().x()+y/r.scintillator_x_mm*box.width(), box.center().y()-z/r.scintillator_y_mm*box.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.colors
        p.fillRect(self.rect(), QColor(c['panel']))
        if self.state is None:
            p.end(); return
        box, r, state = self.image_rect(), self.results, self.state
        if self.image is not None and self.image_revision == self.revision:
            p.drawImage(box, self.image)
        else:
            p.fillRect(box, QColor(c['raised']))
            p.setPen(QColor(c['muted']))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, "Calculating projection…")
        p.setPen(pen(c['muted'])); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(box)
        p.save(); p.setClipRect(box)
        crop_w = box.width()*r.crop_nx/r.output_nx
        crop_h = box.height()*r.crop_ny/r.output_ny
        crop = QRectF(box.center().x()-crop_w/2, box.center().y()-crop_h/2, crop_w, crop_h)
        if crop != box:
            shade = QColor(c['bg']); shade.setAlpha(140)
            p.fillRect(QRectF(box.left(), box.top(), box.width(), crop.top()-box.top()), shade)
            p.fillRect(QRectF(box.left(), crop.bottom(), box.width(), box.bottom()-crop.bottom()), shade)
            p.fillRect(QRectF(box.left(), crop.top(), crop.left()-box.left(), crop.height()), shade)
            p.fillRect(QRectF(crop.right(), crop.top(), box.right()-crop.right(), crop.height()), shade)
            p.setPen(pen(c['cyan'], 1.3, Qt.PenStyle.DashLine)); p.drawRect(crop)
        if self.grid:
            p.setPen(pen("#61788d", 0.6))
            for i in range(1, min(64, r.output_nx)):
                x = box.left()+box.width()*i/min(64, r.output_nx)
                p.drawLine(QPointF(x, box.top()), QPointF(x, box.bottom()))
            for i in range(1, min(64, r.output_ny)):
                y = box.top()+box.height()*i/min(64, r.output_ny)
                p.drawLine(QPointF(box.left(), y), QPointF(box.right(), y))
        if state.phantom.roi_enabled:
            yz, _ = project_points(phantom_points(state.phantom, roi=True), state.geometry)
            pts = [self.map_yz(pos) for pos in hull(yz)]
            from PySide6.QtGui import QPolygonF
            p.setPen(pen(c['cyan'], 1.7, Qt.PenStyle.DashLine)); p.drawPolygon(QPolygonF(pts))
        if self.annotations:
            for i, pt in enumerate(marker_points(state.phantom)):
                info = inspect_point(pt, state.geometry, state.profile.detector)
                pos = self.map_yz(info.scintillator_mm[1:])
                p.setPen(pen(c['cyan'] if i == self.selected_marker else c['amber'], 1.5))
                p.drawEllipse(pos, 6 if i == self.selected_marker else 4, 6 if i == self.selected_marker else 4)
                p.setPen(QColor("#15243b"))
                p.drawText(pos+QPointF(8, -6), chr(65+i))
            if self.cursor_pos is not None:
                p.setPen(pen(c['cyan'], 1))
                p.drawLine(self.cursor_pos+QPointF(-8, 0), self.cursor_pos+QPointF(8, 0))
                p.drawLine(self.cursor_pos+QPointF(0, -8), self.cursor_pos+QPointF(0, 8))
        p.restore()
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(c['muted']))
        p.drawText(QRectF(5, box.bottom()+5, self.width()-10, 17), Qt.AlignmentFlag.AlignCenter,
                   f"{r.crop_nx} × {r.crop_ny} acquired px · {r.sampling_um:.4g} µm/px")
        if self.annotations:
            length = min(5, r.fov_x_mm/4)
            pixels = length/r.fov_x_mm*box.width()
            x, y = box.left()+10, box.bottom()-13
            p.setPen(pen("#202d3c", 2))
            p.drawLine(QPointF(x, y), QPointF(x+pixels, y))
            p.drawLine(QPointF(x, y-3), QPointF(x, y+3))
            p.drawLine(QPointF(x+pixels, y-3), QPointF(x+pixels, y+3))
            p.drawText(QPointF(x, y-6), f"{length:.3g} mm at center")
        p.end()

    def mouseMoveEvent(self, event):
        box = self.image_rect()
        pos = event.position()
        if self.state is None or not box.contains(pos):
            self.hovered.emit(None); self.cursor_pos = None; self.update(); return
        r, d = self.results, self.state.profile.detector
        y = (pos.x()-box.center().x())/box.width()*r.scintillator_x_mm
        z = -(pos.y()-box.center().y())/box.height()*r.scintillator_y_mm
        camera = np.array([y, z])*d.optical_m
        uv = camera/(d.binning*d.pitch_um/1000)+(np.array([r.output_nx, r.output_ny])-1)/2
        yz = np.array([-y if d.flip_y else y, -z if d.flip_z else z])
        lengths, inc = ray_path_lengths(self.state.geometry, self.state.phantom, yz)
        self.cursor_info.emit(f"Detector ({yz[0]:.3f}, {yz[1]:.3f}) mm · pixel (u,v)=({uv[0]:.1f}, {uv[1]:.1f})\nHost path {float(lengths):.3f} mm; inclusion path {float(inc):.3f} mm. v is physical up.")
        self.hovered.emit(tuple(yz))
        self.cursor_pos = pos
        self.update()

    def leaveEvent(self, event):
        self.hovered.emit(None)
        self.cursor_pos = None
        self.update()

    def mousePressEvent(self, event):
        if self.state:
            for i, pt in enumerate(marker_points(self.state.phantom)):
                yz, _ = project_points(pt, self.state.geometry)
                point = self.map_yz(yz)
                if (point-event.position()).manhattanLength() < 16:
                    self.marker_selected.emit(i)
                    return

    def export_image(self, path, annotated=True):
        if annotated:
            if not self.grab().save(str(path)):
                raise OSError("Could not save annotated projection")
        elif self.image is not None and self.image_revision == self.revision:
            if not self.image.save(str(path)):
                raise OSError("Could not save projection")
        else:
            raise ValueError("Wait for the current projection to finish")
