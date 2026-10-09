"""Typed, serializable model. Lengths are mm unless a name explicitly says otherwise."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import math

MANUAL = "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf"
WHITEPAPER = "https://asset-downloads.zeiss.com/catalogs/download/mic/02632a56-567c-4a98-b8a7-e9bd31e3f5cc/APAC-only_EN_wp_expanding_boundaries_3D_X-ray_Versa_515.pdf"
BOUND_KEYS = ("a_min", "a_max", "b_min", "b_max", "D_min", "D_max", "source_clearance", "detector_clearance")


def finite(value: float, name: str, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class Quantity:
    value: float | None = None
    units: str = "mm"
    origin: str = "user supplied"
    confirmed: bool = False
    source: str = ""
    version: str = ""
    date: str = ""

    def validate(self):
        if type(self.confirmed) is not bool:
            raise ValueError("Quantity confirmation must be a boolean")
        if self.value is not None:
            finite(self.value, "Profile quantity")
        if self.origin not in ("user supplied", "nominal", "calibrated", "reference"):
            raise ValueError("Unknown quantity provenance")
        if self.units not in ("mm", "µm", "pixels", "×", "dimensionless", "degrees"):
            raise ValueError(f"Unsupported quantity units: {self.units}")


@dataclass(frozen=True)
class GeometryInputs:
    a_mm: float = 205.0
    b_mm: float = 267.32

    def validate(self):
        finite(self.a_mm, "Source distance a (mm)", True)
        finite(self.b_mm, "Scintillator distance b (mm)", True)


@dataclass(frozen=True)
class DetectorProfile:
    nx: int = 2048
    ny: int = 2048
    pitch_um: float = 13.5
    optical_m: float = 0.4
    binning: int = 1
    usable_nx: int | None = None
    usable_ny: int | None = None
    image_circle_mm: float | None = None
    crop_nx: int | None = None
    crop_ny: int | None = None
    flip_y: bool = False
    flip_z: bool = False
    provenance: dict[str, Quantity] = field(default_factory=lambda: {
        "nx": Quantity(2048, "pixels", "reference", False, MANUAL, "v11.x, Table H-6"),
        "ny": Quantity(2048, "pixels", "reference", False, MANUAL, "v11.x, Table H-6"),
        "pitch_um": Quantity(13.5, "µm", "reference", False, MANUAL, "v11.x, Table H-6"),
        "optical_m": Quantity(0.4, "×", "nominal", False),
    })

    def output_shape(self) -> tuple[int, int]:
        """Centered usable rectangle inscribed in any configured image circle."""
        nx, ny = self.usable_nx or self.nx, self.usable_ny or self.ny
        if self.image_circle_mm is not None:
            diag = math.hypot(nx, ny) * self.pitch_um / 1000 / self.optical_m
            ratio = min(1.0, self.image_circle_mm / diag)
            nx, ny = math.floor(nx * ratio), math.floor(ny * ratio)
        return nx // self.binning, ny // self.binning

    def validate(self):
        if type(self.flip_y) is not bool or type(self.flip_z) is not bool:
            raise ValueError("Optical parity flags must be booleans")
        for n, v in (("Native columns", self.nx), ("Native rows", self.ny)):
            if type(v) is not int or not 1 <= v <= 100000:
                raise ValueError(f"{n} must be an integer from 1 to 100000")
        finite(self.pitch_um, "Camera pitch (µm)", True)
        finite(self.optical_m, "Optical magnification", True)
        if type(self.binning) is not int or self.binning not in (1, 2, 4, 8):
            raise ValueError("Binning must be 1, 2, 4, or 8")
        if self.nx % self.binning or self.ny % self.binning:
            raise ValueError("Native dimensions must be divisible by binning")
        for name, v, n in (("Usable columns", self.usable_nx, self.nx), ("Usable rows", self.usable_ny, self.ny)):
            if v is not None and (type(v) is not int or not 1 <= v <= n or v % self.binning):
                raise ValueError(f"{name} must fit native pixels and be divisible by binning")
        if self.image_circle_mm is not None:
            finite(self.image_circle_mm, "Scintillator image circle (mm)", True)
        ox, oy = self.output_shape()
        if min(ox, oy) < 1:
            raise ValueError("Usable image area contains no complete binned pixels")
        for name, v, n in (("Crop columns", self.crop_nx, ox), ("Crop rows", self.crop_ny, oy)):
            if v is not None and (type(v) is not int or not 1 <= v <= n):
                raise ValueError(f"{name} must be between 1 and {n} binned pixels")
        for q in self.provenance.values():
            q.validate()


@dataclass(frozen=True)
class AngleConstraint:
    limit_deg: float | None = 12.0
    axis: str = "diagonal"
    convention: str = "full"
    envelope: str = "active"
    strict: bool = True
    buffer_deg: float = 0.02

    def validate(self):
        if type(self.strict) is not bool:
            raise ValueError("Strict angle flag must be a boolean")
        if self.axis not in ("horizontal", "vertical", "diagonal"):
            raise ValueError("Angle axis must be horizontal, vertical, or diagonal")
        if self.convention not in ("full", "half") or self.envelope not in ("active", "crop"):
            raise ValueError("Unknown angle convention or acquisition envelope")
        finite(self.buffer_deg, "Angular buffer (degrees)")
        if self.buffer_deg < 0:
            raise ValueError("Angular buffer cannot be negative")
        if self.limit_deg is not None:
            finite(self.limit_deg, "Angle limit (degrees)", True)
            max_angle = 180 if self.convention == "full" else 90
            if self.limit_deg >= max_angle or self.buffer_deg >= self.limit_deg:
                raise ValueError(f"Angle must be below {max_angle}° and above its buffer")


@dataclass(frozen=True)
class ImagingRequirements:
    sampling_um: float | None = 14.6484375
    sampling_mode: str = "exact"
    fov_x_mm: float | None = 30.0
    fov_y_mm: float | None = 30.0
    margin_mm: float = 0.0  # added on each side
    fixed_kind: str = "none"
    fixed_mm: float | None = None
    goal: str = "minimum separation"

    def validate(self):
        for name, value in (("Requested sampling (µm)", self.sampling_um), ("FOV width (mm)", self.fov_x_mm), ("FOV height (mm)", self.fov_y_mm)):
            if value is not None:
                finite(value, name, True)
        finite(self.margin_mm, "Margin (mm)")
        if self.margin_mm < 0:
            raise ValueError("FOV margin cannot be negative")
        if self.sampling_mode not in ("exact", "no coarser"):
            raise ValueError("Unknown sampling requirement")
        if self.goal not in ("minimum separation", "closest to current distances"):
            raise ValueError("Unknown solver goal")
        if self.fixed_kind not in ("none", "a", "b", "D"):
            raise ValueError("Choose no fixed distance, a, b, or D")
        if self.fixed_kind != "none":
            finite(self.fixed_mm, "Fixed distance (mm)", True)


@dataclass(frozen=True)
class CoordinateMapping:
    """Verified affine mapping of documented signed stage separation to a,b.

    stage_separation_mm = coeff_a*a_mm + coeff_b*b_mm + offset_mm.
    No sign or offset is guessed. Verifying this is a local calibration action.
    """
    verified: bool = False
    coeff_a: float | None = None
    coeff_b: float | None = None
    offset_mm: float | None = None
    source: str = ""

    def validate(self):
        if type(self.verified) is not bool:
            raise ValueError("Mapping verification must be a boolean")
        for v in (self.coeff_a, self.coeff_b, self.offset_mm):
            if v is not None:
                finite(v, "Coordinate mapping coefficient")
        if self.verified and (None in (self.coeff_a, self.coeff_b, self.offset_mm) or not self.source.strip()):
            raise ValueError("Verified mapping requires all coefficients and a calibration source")


@dataclass(frozen=True)
class ObjectiveCalibration:
    detector: DetectorProfile = field(default_factory=DetectorProfile)
    availability: str = "unconfigured"
    bounds: dict[str, Quantity] = field(default_factory=dict)
    notes: str = "Nominal optical scale; confirm installed configuration."


def default_objectives():
    return {f"{m:g}×": ObjectiveCalibration(
        DetectorProfile(optical_m=m, provenance={
            **DetectorProfile().provenance,
            "optical_m": Quantity(m, "×", "nominal", False),
        })) for m in (0.4, 4, 20, 40)}


@dataclass(frozen=True)
class InstrumentProfile:
    name: str = "ZEISS Versa — 2048 × 2048, 13.5 µm, 0.4×"
    selected_objective: str = "0.4×"
    objectives: dict[str, ObjectiveCalibration] = field(default_factory=default_objectives)
    bounds: dict[str, Quantity] = field(default_factory=lambda: {key: Quantity() for key in BOUND_KEYS})
    mapping: CoordinateMapping = field(default_factory=CoordinateMapping)
    legacy_stage_min: Quantity = field(default_factory=lambda: Quantity(
        135.0, "mm", "reference", False, MANUAL, "v11.x, Table 2-3 (0.4× only)"))
    focal_spot_um: Quantity = field(default_factory=lambda: Quantity(None, "µm"))
    notes: str = "Model demonstration. Hardware travel and clearances are unconfigured. Legacy manual values require local confirmation; stage coordinates are not physical distances."

    @property
    def detector(self):
        return self.objectives[self.selected_objective].detector

    def with_detector(self, detector):
        objective = replace(self.objectives[self.selected_objective], detector=detector)
        return replace(self, objectives={**self.objectives, self.selected_objective: objective})

    def validate(self):
        if not self.name.strip() or self.selected_objective not in self.objectives:
            raise ValueError("Profile needs a name and a valid selected objective")
        self.mapping.validate()
        self.legacy_stage_min.validate()
        if self.legacy_stage_min.units != "mm" or (self.legacy_stage_min.value is not None and self.legacy_stage_min.value <= 0):
            raise ValueError("Legacy stage minimum must be positive mm")
        self.focal_spot_um.validate()
        if self.focal_spot_um.units != "µm" or (self.focal_spot_um.value is not None and self.focal_spot_um.value <= 0):
            raise ValueError("Focal spot must be positive µm, or unconfigured")
        for bounds in [self.bounds] + [o.bounds for o in self.objectives.values()]:
            for key, q in bounds.items():
                if key not in BOUND_KEYS:
                    raise ValueError(f"Unknown physical bound: {key}")
                q.validate()
                if q.units != "mm" or (q.value is not None and q.value <= 0):
                    raise ValueError(f"{key} must be positive and in mm")
        for obj in self.objectives.values():
            obj.detector.validate()
            if obj.availability not in ("unconfigured", "available", "unavailable"):
                raise ValueError("Unknown objective availability")


@dataclass(frozen=True)
class Phantom:
    shape: str = "cuboid"
    width_mm: float = 28.0  # y
    height_mm: float = 28.0  # z
    depth_mm: float = 5.0  # x
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    offset_z_mm: float = 0.0
    rotation_deg: float = 0.0
    mu_mm_inv: float = 0.055
    inclusion_mu_mm_inv: float = 0.22
    roi_width_mm: float = 10.0
    roi_height_mm: float = 10.0
    roi_depth_mm: float = 3.0
    roi_enabled: bool = False
    roi_offset_x_mm: float = 0.0
    roi_offset_y_mm: float = 0.0
    roi_offset_z_mm: float = 0.0

    def validate(self):
        if type(self.roi_enabled) is not bool:
            raise ValueError("ROI flag must be a boolean")
        if self.shape not in ("cuboid", "ellipsoid"):
            raise ValueError("Choose cuboid or ellipsoid")
        for name in ("width_mm", "height_mm", "depth_mm", "roi_width_mm", "roi_height_mm", "roi_depth_mm"):
            finite(getattr(self, name), name, True)
        for name in ("offset_x_mm", "offset_y_mm", "offset_z_mm", "rotation_deg", "mu_mm_inv", "inclusion_mu_mm_inv", "roi_offset_x_mm", "roi_offset_y_mm", "roi_offset_z_mm"):
            finite(getattr(self, name), name)
        if min(self.mu_mm_inv, self.inclusion_mu_mm_inv) < 0:
            raise ValueError("Attenuation coefficients must be nonnegative mm⁻¹")


@dataclass(frozen=True)
class AppState:
    geometry: GeometryInputs = field(default_factory=GeometryInputs)
    profile: InstrumentProfile = field(default_factory=InstrumentProfile)
    requirements: ImagingRequirements = field(default_factory=ImagingRequirements)
    angle: AngleConstraint = field(default_factory=AngleConstraint)
    phantom: Phantom = field(default_factory=Phantom)
    mode: str = "Explore geometry"

    def validate(self):
        self.geometry.validate()
        self.profile.validate()
        self.requirements.validate()
        self.angle.validate()
        self.phantom.validate()
        if self.mode not in ("Explore geometry", "Plan acquisition", "Lock magnification", "Lock total separation"):
            raise ValueError("Unknown interaction mode")

