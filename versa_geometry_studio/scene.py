"""Equal-scale orthographic QGraphicsViews with custom QPainter hardware and rays."""
import math
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath, QPolygonF, QFont, QImage
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView
from .projection import phantom_points, marker_points, project_points, inspect_point
from .theme import DARK


def hull(points):
    pts = sorted(set(map(tuple, points)))
    if len(pts) <= 2:
        return pts
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for point in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1]+upper[:-1]


def pen(color, width=1, style=Qt.PenStyle.SolidLine):
    result = QPen(QColor(color), width)
    result.setCosmetic(True)
    result.setStyle(style)
    return result


def polygon(points):
    return QPolygonF([QPointF(float(x), float(y)) for x, y in points])


class GeometryItem(QGraphicsItem):
    def __init__(self, axis):
        super().__init__()
        self.axis = axis
        self.state = self.results = None
        self.colors = DARK
        self.rect = QRectF(-280, -100, 740, 220)
        self.hover_yz = None
        self.selected_marker = 0
        self.corner_rays = False

    def boundingRect(self):
        return self.rect

    def set_state(self, state, results):
        self.prepareGeometryChange()
        self.state, self.results = state, results
        max_size = max(results.scintillator_x_mm, results.scintillator_y_mm, state.phantom.height_mm, state.phantom.width_mm)
        half_height = max(105, max_size/2+65)
        self.rect = QRectF(-results.a_mm-70, -half_height, results.D_mm+230, half_height*2+5)
        points = phantom_points(state.phantom)
        axis_index = 1 if self.axis == "top" else 2
        self.outline = hull(np.stack([points[:, 0], -points[:, axis_index]], axis=-1))
        self.markers = marker_points(state.phantom)
        self.update()

    def text(self, painter, x, y, text, color=None, size=10, centered=False):
        scale = max(abs(painter.worldTransform().m11()), 0.01)
        font = QFont("Segoe UI")
        font.setPixelSize(max(1, round(size/scale)))
        painter.setFont(font)
        painter.setPen(QColor(color or self.colors['muted']))
        rect = painter.fontMetrics().boundingRect(text)
        if centered:
            x -= rect.width()/2
        painter.drawText(QPointF(x, y), text)

    def dimension(self, p, x1, x2, y, text):
        c = self.colors
        p.setPen(pen(c['muted']))
        p.drawLine(QPointF(x1, y), QPointF(x2, y))
        for x, direction in ((x1, 1), (x2, -1)):
            p.drawLine(QPointF(x, y-5), QPointF(x, y+5))
            p.drawLine(QPointF(x, y), QPointF(x+direction*5, y-2))
            p.drawLine(QPointF(x, y), QPointF(x+direction*5, y+2))
        self.text(p, (x1+x2)/2, y-7, text, c['text'], 10, True)

    def paint(self, p, option, widget=None):
        if self.state is None:
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c, r, st = self.colors, self.results, self.state
        a, b = r.a_mm, r.b_mm
        index = 1 if self.axis == "top" else 2
        extent = (r.scintillator_x_mm if index == 1 else r.scintillator_y_mm)/2
        crop_extent = (r.crop_scintillator_x_mm if index == 1 else r.crop_scintillator_y_mm)/2
        field = extent/r.geometrical_m
        # True physical grid; both scene axes have the same scaling.
        p.setPen(pen(c['grid'], 0.7))
        grid_step = max(10, 10**math.floor(math.log10(max(r.D_mm, 1)))/5)
        for x in np.arange(math.floor(self.rect.left()/grid_step)*grid_step, self.rect.right(), grid_step):
            p.drawLine(QPointF(x, self.rect.top()), QPointF(x, self.rect.bottom()))
        for y in np.arange(math.floor(self.rect.top()/grid_step)*grid_step, self.rect.bottom(), grid_step):
            p.drawLine(QPointF(self.rect.left(), y), QPointF(self.rect.right(), y))
        fill = QColor(c['amber']); fill.setAlpha(18)
        p.setBrush(fill); p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(polygon([(-a, 0), (b, -extent), (b, extent)]))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen(c['amber'], 1.2))
        for edge in (-extent, extent):
            p.drawLine(QPointF(-a, 0), QPointF(b, edge))
        if abs(crop_extent-extent) > 1e-8:
            p.setPen(pen(c['cyan'], 1, Qt.PenStyle.DashLine))
            for edge in (-crop_extent, crop_extent):
                p.drawLine(QPointF(-a, 0), QPointF(b, edge))
        p.setPen(pen(c['muted'], 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(-a, 0), QPointF(b, 0))
        p.drawLine(QPointF(0, -field-15), QPointF(0, field+15))
        # Center-plane field, not the specimen's extent.
        p.setPen(pen(c['cyan'], 2))
        p.drawLine(QPointF(0, -field), QPointF(0, field))
        for y in (-field, field):
            p.drawLine(QPointF(-7, y), QPointF(7, y))
        self.text(p, 18, -field-9, f"FOV {2*field:.3g} mm", c['cyan'])
        # Phantom, at its physical depth, offset, and rotation.
        fill = QColor(c['cyan']); fill.setAlpha(40)
        p.setBrush(fill); p.setPen(pen(c['cyan'], 1.3))
        p.drawPolygon(polygon(self.outline))
        if st.phantom.roi_enabled:
            roi = phantom_points(st.phantom, roi=True)
            p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(pen(c['cyan'], 1.5, Qt.PenStyle.DashLine))
            p.drawPolygon(polygon(hull(np.stack([roi[:, 0], -roi[:, index]], axis=-1))))
        for i, point in enumerate(self.markers):
            info = inspect_point(point, st.geometry, st.profile.detector)
            endpoint = info.scintillator_mm[index]
            color = c['red'] if info.clipped_active else c['amber']
            p.setPen(pen(color, 1.8 if i == self.selected_marker else 0.65))
            p.drawLine(QPointF(-a, 0), QPointF(b, -endpoint))
            p.setBrush(QColor(c['cyan'] if i == self.selected_marker else c['amber']))
            p.drawEllipse(QPointF(point[0], -point[index]), 2.4, 2.4)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if i == self.selected_marker:
                p.drawEllipse(QPointF(point[0], -point[index]), 5, 5)
        if self.corner_rays:
            points = phantom_points(st.phantom)
            yz, _ = project_points(points, st.geometry)
            p.setPen(pen(c['amber'], 0.5, Qt.PenStyle.DotLine))
            for pt in yz[::max(1, len(yz)//8)]:
                p.drawLine(QPointF(-a, 0), QPointF(b, -pt[index-1]))
        if self.hover_yz is not None:
            p.setPen(pen(c['cyan'], 2.1))
            p.drawLine(QPointF(-a, 0), QPointF(b, -self.hover_yz[index-1]))
        # X-ray tube: focal spot is exactly x=-a. Housing is illustrative.
        p.setPen(pen(c['amber'], 1.4)); p.setBrush(QColor(c['raised']))
        p.drawRoundedRect(QRectF(-a-42, -21, 37, 42), 6, 6)
        p.drawRoundedRect(QRectF(-a-34, -29, 18, 8), 2, 2)
        p.setBrush(QColor(c['amber']))
        p.drawPolygon(polygon([(-a-20, -12), (-a-8, -4), (-a-17, 11)]))
        p.drawEllipse(QPointF(-a, 0), 2.5, 2.5)
        # Rotation platform artwork; origin remains physical (0,0,0).
        p.setPen(pen(c['muted'])); p.setBrush(QColor(c['raised']))
        platform_y = max(25, st.phantom.height_mm/2+8) if index == 2 else 30
        p.drawRoundedRect(QRectF(-17, platform_y, 34, 6), 2, 2)
        p.drawLine(QPointF(-8, platform_y+8), QPointF(8, platform_y+8))
        p.setPen(pen(c['cyan'])); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(-11, platform_y+11, 22, 8), 25*16, 280*16)
        # Scintillator ends the X-rays; optical relay is a separate schematic.
        p.setBrush(QColor(c['cyan'])); p.setPen(pen(c['cyan'], 2))
        p.drawRoundedRect(QRectF(b-2, -extent, 4, 2*extent), 1, 1)
        optical_x, camera_x = b+45, b+90
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(pen(c['violet'], 1, Qt.PenStyle.DashLine))
        for sign in (-1, 1):
            p.drawPolyline(polygon([(b+3, sign*min(extent, 20)), (optical_x, sign*10), (camera_x, sign*13)]))
        p.setBrush(QColor(c['raised'])); p.setPen(pen(c['violet'], 1.4))
        p.drawRoundedRect(QRectF(optical_x-11, -17, 22, 34), 5, 5)
        p.drawEllipse(QRectF(optical_x-4, -15, 8, 30))
        p.drawRoundedRect(QRectF(camera_x, -22, 33, 44), 5, 5)
        p.setBrush(QColor(c['violet'])); p.drawRect(QRectF(camera_x+5, -14, 3, 28))
        self.text(p, -a-17, -56, "X-RAY SOURCE", c['amber'], 10, True)
        self.text(p, 0, -65, "ROTATING SAMPLE", c['text'], 10, True)
        self.text(p, b, -extent-14, "SCINTILLATOR", c['cyan'], 10, True)
        self.text(p, optical_x+20, -78, "OPTICS → CAMERA", c['violet'], 10, True)
        self.text(p, optical_x+24, 39, f"m = {st.profile.detector.optical_m:g}× · schematic", c['violet'], 9, True)
        dim_y = max(66, extent+30, platform_y+28)
        self.dimension(p, -a, 0, dim_y, f"a = {a:.3f} mm")
        self.dimension(p, 0, b, dim_y, f"b = {b:.3f} mm")
        self.dimension(p, -a, b, dim_y+25, f"D = {r.D_mm:.3f} mm")
        # Show only the angle belonging to this orthographic plane.
        which = "horizontal" if index == 1 else "vertical"
        half = (r.half_angles_rad if st.angle.envelope == "active" else r.crop_half_angles_rad)[index-1]
        radius = min(55, r.D_mm/6)
        p.setPen(pen(c['amber'], 1.4)); p.setBrush(Qt.BrushStyle.NoBrush)
        if st.angle.convention == "full":
            p.drawArc(QRectF(-a-radius, -radius, radius*2, radius*2), round(-math.degrees(half)*16), round(math.degrees(half)*32))
            arc_label = f"θ {which[0]} = {math.degrees(half)*2:.3f}° full"
        else:
            p.drawArc(QRectF(-a-radius, -radius, radius*2, radius*2), 0, round(math.degrees(half)*16))
            arc_label = f"α {which[0]} = {math.degrees(half):.3f}° half"
        self.text(p, -a+radius+5, -10, arc_label, c['amber'], 9)
        self.text(p, self.rect.left()+8, self.rect.top()+17, f"{'TOP  x–y' if index == 1 else 'SIDE  x–z'}   /   grid {grid_step:g} mm · equal axis scale", c['muted'], 10)
        p.setPen(pen(c['cyan'])); p.drawEllipse(QPointF(0, 0), 1.5, 1.5)


class GeometryView(QGraphicsView):
    distance_moved = Signal(str, float)
    drag_started = Signal()
    drag_finished = Signal()
    marker_selected = Signal(int)

    def __init__(self, axis):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = GeometryItem(axis)
        self.scene().addItem(self.item)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumHeight(140)
        self.setMouseTracking(True)
        self.setToolTip("Drag tube or scintillator to move. Wheel to zoom, middle-drag to pan. Select an inclusion to inspect its ray.")
        self.dragging = None
        self.pan_pos = None
        self.auto_fit = True
        self.set_theme(DARK)

    def set_theme(self, colors):
        self.item.colors = colors
        self.setBackgroundBrush(QColor(colors['panel']))
        self.item.update()

    def set_state(self, state, results):
        self.item.set_state(state, results)
        self.scene().setSceneRect(self.item.rect)
        if self.auto_fit and not self.dragging:
            self.fit()

    def fit(self):
        self.auto_fit = True
        self.fitInView(self.item.rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto_fit:
            self.fit()

    def wheelEvent(self, event):
        self.auto_fit = False
        scale = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        self.scale(scale, scale)
        event.accept()

    def mousePressEvent(self, event):
        point = self.mapToScene(event.position().toPoint())
        if event.button() == Qt.MouseButton.MiddleButton:
            self.pan_pos = event.position().toPoint()
            self.auto_fit = False
            return
        if event.button() == Qt.MouseButton.LeftButton and self.item.results:
            r = self.item.results
            if -r.a_mm-47 <= point.x() <= -r.a_mm+12 and abs(point.y()) < 33:
                self.dragging = "a"
            elif abs(point.x()-r.b_mm) < 15 and abs(point.y()) < max(r.scintillator_x_mm, r.scintillator_y_mm)/2+12:
                self.dragging = "b"
            if self.dragging:
                self.drag_offset = point.x() - (-r.a_mm if self.dragging == "a" else r.b_mm)
                self.drag_started.emit()
                return
            index = 1 if self.item.axis == "top" else 2
            for i, marker in enumerate(self.item.markers):
                if math.hypot(marker[0]-point.x(), -marker[index]-point.y())*self.transform().m11() < 9:
                    self.marker_selected.emit(i)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.pan_pos is not None:
            delta = event.position().toPoint()-self.pan_pos
            self.pan_pos = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-delta.y())
            return
        if self.dragging:
            x = self.mapToScene(event.position().toPoint()).x()-self.drag_offset
            self.distance_moved.emit(self.dragging, -x if self.dragging == "a" else x)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = None
            self.drag_finished.emit()
        self.pan_pos = None
        super().mouseReleaseEvent(event)


def export_geometry(path, views):
    width, height = 1600, 960
    if str(path).lower().endswith(".svg"):
        device = QSvgGenerator()
        device.setFileName(str(path))
        from PySide6.QtCore import QSize
        device.setSize(QSize(width, height))
        device.setViewBox(QRectF(0, 0, width, height))
        device.setTitle("Versa Geometry Studio — physical ray geometry")
    else:
        device = QImage(width, height, QImage.Format.Format_ARGB32)
        device.fill(QColor(views[0].item.colors['panel']))
    painter = QPainter(device)
    try:
        painter.fillRect(QRectF(0, 0, width, height), QColor(views[0].item.colors['panel']))
        painter.setPen(QColor(views[0].item.colors['text']))
        painter.setFont(QFont("Segoe UI", 18))
        painter.drawText(QPointF(35, 40), "VERSA GEOMETRY STUDIO  /  TWO-STAGE MAGNIFICATION")
        state, r = views[0].item.state, views[0].item.results
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(QPointF(35, 72), f"Selected: {state.angle.axis} {state.angle.convention} {r.selected_angle_deg(state.angle):.9f}° · {state.angle.envelope} envelope. Diagonal is a 3D corner cone.")
        for i, view in enumerate(views):
            view.scene().render(painter, QRectF(20, 100+i*400, width-40, 390), view.item.rect, Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawText(QPointF(35, 940), "X-rays terminate at the scintillator. Optical relay spacing and hardware artwork are schematic; dimension labels are physical mm.")
    finally:
        painter.end()
    if isinstance(device, QImage) and not device.save(str(path)):
        raise OSError(f"Could not save image: {path}")
