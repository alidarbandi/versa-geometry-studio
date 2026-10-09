"""Authoritative two-stage magnification and angle calculations (no Qt)."""
from dataclasses import dataclass
import math
from .models import DetectorProfile, GeometryInputs, AngleConstraint, finite

ALGEBRA_TOL = 1e-9
ANGLE_TOL_DEG = 1e-9


@dataclass(frozen=True)
class GeometryResults:
    a_mm: float
    b_mm: float
    D_mm: float
    geometrical_m: float
    total_m: float
    camera_x_mm: float
    camera_y_mm: float
    scintillator_x_mm: float
    scintillator_y_mm: float
    crop_scintillator_x_mm: float
    crop_scintillator_y_mm: float
    output_nx: int
    output_ny: int
    crop_nx: int
    crop_ny: int
    sampling_um: float
    fov_x_mm: float
    fov_y_mm: float
    crop_fov_x_mm: float
    crop_fov_y_mm: float
    half_angles_rad: tuple[float, float, float]
    crop_half_angles_rad: tuple[float, float, float]

    def angles_deg(self, angle: AngleConstraint):
        vals = self.half_angles_rad if angle.envelope == "active" else self.crop_half_angles_rad
        scale = 2 if angle.convention == "full" else 1
        return tuple(math.degrees(v) * scale for v in vals)

    def selected_angle_deg(self, angle):
        return self.angles_deg(angle)[("horizontal", "vertical", "diagonal").index(angle.axis)]


def magnification(geometry: GeometryInputs) -> float:
    geometry.validate()
    value = 1 + geometry.b_mm / geometry.a_mm
    finite(value, "Calculated geometrical magnification", True)
    return value


def cone_half_angles(width_mm, height_mm, distance_mm):
    for name, v in (("Detector width", width_mm), ("Detector height", height_mm), ("Separation", distance_mm)):
        finite(v, name, True)
    return tuple(math.atan(r / distance_mm) for r in (width_mm/2, height_mm/2, math.hypot(width_mm, height_mm)/2))


def calculate(g: GeometryInputs, d: DetectorProfile) -> GeometryResults:
    g.validate()
    d.validate()
    mg, D = magnification(g), g.a_mm + g.b_mm
    finite(D, "Calculated separation (mm)", True)
    pitch_mm = d.pitch_um / 1000
    ox, oy = d.output_shape()
    cx, cy = d.crop_nx or ox, d.crop_ny or oy
    wx, wy = ox*d.binning*pitch_mm/d.optical_m, oy*d.binning*pitch_mm/d.optical_m
    crop_wx, crop_wy = cx*d.binning*pitch_mm/d.optical_m, cy*d.binning*pitch_mm/d.optical_m
    delta_um = d.binning*d.pitch_um/(d.optical_m*mg)
    for name, value in (("Active scintillator width", wx), ("Active scintillator height", wy), ("Acquired sampling", delta_um)):
        finite(value, name, True)
    return GeometryResults(g.a_mm, g.b_mm, D, mg, mg*d.optical_m,
        d.nx*pitch_mm, d.ny*pitch_mm, wx, wy, crop_wx, crop_wy,
        ox, oy, cx, cy, delta_um, wx/mg, wy/mg, crop_wx/mg, crop_wy/mg,
        cone_half_angles(wx, wy, D), cone_half_angles(crop_wx, crop_wy, D))


def distances_at_separation(mg: float, D_mm: float) -> GeometryInputs:
    finite(mg, "Geometrical magnification", True)
    finite(D_mm, "Separation (mm)", True)
    if mg <= 1:
        raise ValueError("M_g = 1 is a b = 0 limiting family; positive detector distance requires M_g > 1")
    return GeometryInputs(D_mm/mg, D_mm - D_mm/mg)


def angle_distance_min(width_mm, height_mm, constraint: AngleConstraint, buffered=False):
    constraint.validate()
    if constraint.limit_deg is None:
        return None
    radius = {"horizontal": width_mm/2, "vertical": height_mm/2, "diagonal": math.hypot(width_mm, height_mm)/2}[constraint.axis]
    angle = constraint.limit_deg - (constraint.buffer_deg if buffered else 0)
    half_rad = math.radians(angle / (2 if constraint.convention == "full" else 1))
    return radius / math.tan(half_rad)


def angle_passes(r: GeometryResults, c: AngleConstraint, buffered=False):
    if c.limit_deg is None:
        return True
    actual = r.selected_angle_deg(c)
    limit = c.limit_deg - (c.buffer_deg if buffered else 0)
    return actual < limit - ANGLE_TOL_DEG if c.strict else actual <= limit + ANGLE_TOL_DEG


def required_crop(length_mm: float, sampling_um: float):
    finite(length_mm, "Required coverage (mm)", True)
    finite(sampling_um, "Sampling (µm)", True)
    pixels = math.ceil(length_mm*1000/sampling_um - 1e-10)
    return pixels, pixels*sampling_um/1000


def effective_optical_factor(g, pitch_um, binning, measured_sampling_um):
    for n, v in (("Pitch (µm)", pitch_um), ("Measured sampling (µm)", measured_sampling_um)):
        finite(v, n, True)
    if binning not in (1, 2, 4, 8):
        raise ValueError("Invalid calibration binning")
    return binning*pitch_um/(measured_sampling_um*magnification(g))


def penumbra_um(focal_spot_um, mg):
    finite(focal_spot_um, "Focal spot (µm)", True)
    finite(mg, "Magnification", True)
    if mg < 1:
        raise ValueError("Penumbra requires M_g >= 1")
    return focal_spot_um*(mg-1)/mg
