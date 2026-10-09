"""Deterministic acquisition planner.

Imaging ratios become linear half planes in (a,b). Enumerating their vertices
solves minimum separation exactly; orthogonal projections also solve nearest
Euclidean distances. No arbitrary exploration limits enter this solver.
"""
from dataclasses import dataclass, field
import math
from .models import AppState, GeometryInputs
from .physics import calculate, angle_distance_min, required_crop, ALGEBRA_TOL

TOL_MM = 1e-7


@dataclass(frozen=True)
class HalfPlane:
    ca: float
    cb: float
    rhs: float
    label: str
    open: bool = False

    def residual(self, a, b):
        return self.ca*a + self.cb*b - self.rhs


@dataclass(frozen=True)
class FeasibilityResult:
    status: str
    explanation: str
    candidate: GeometryInputs | None = None
    magnification_interval: tuple[float, float] | None = None
    source_interval_mm: tuple[float, float] | None = None
    angle_equality_D_mm: float | None = None
    angle_buffered_D_mm: float | None = None
    active_constraints: tuple[str, ...] = ()
    required_crop_pixels: tuple[int | None, int | None] = (None, None)
    achieved_coverage_mm: tuple[float | None, float | None] = (None, None)
    tie_break: str = "Exact locks → minimum D → finest sampling with coverage → closest current pair"


def physical_constraints(state: AppState) -> list[HalfPlane]:
    profile = state.profile
    planes = []
    # Clearances use a conservative full-rotation specimen envelope.
    ph = state.phantom
    radius = math.hypot(ph.depth_mm, ph.width_mm)/2
    for prefix, bounds in (("Profile", profile.bounds), ("Objective", profile.objectives[profile.selected_objective].bounds)):
        for key, q in bounds.items():
            if q.value is None or not q.confirmed:
                continue
            rhs = q.value
            if key == "source_clearance":
                planes.append(HalfPlane(1, 0, rhs + radius - ph.offset_x_mm, f"{prefix} source/sample clearance (rotation envelope)"))
                continue
            if key == "detector_clearance":
                planes.append(HalfPlane(0, 1, rhs + radius + ph.offset_x_mm, f"{prefix} scintillator/sample clearance (rotation envelope)"))
                continue
            ca, cb = {"a": (1, 0), "b": (0, 1), "D": (1, 1)}[key.split("_")[0]]
            sign = -1 if key.endswith("max") else 1
            planes.append(HalfPlane(sign*ca, sign*cb, sign*rhs, f"{prefix} {key} = {rhs:g} mm"))
    mapping, legacy = profile.mapping, profile.legacy_stage_min
    if profile.selected_objective == "0.4×" and mapping.verified and legacy.confirmed and legacy.value is not None:
        planes.append(HalfPlane(mapping.coeff_a, mapping.coeff_b, legacy.value-mapping.offset_mm,
                               "Confirmed legacy stage minimum via verified coordinate mapping"))
    return planes


def source_interval(mg: float, planes: list[HalfPlane]):
    if mg <= 1:
        raise ValueError("M_g <= 1 has no positive-b distance interval")
    lows, highs = [(0.0, "positive a and b")], [(math.inf, "unconfigured upper bound")]
    for p in planes:
        coeff = p.ca + (mg-1)*p.cb
        if coeff == 0:
            if p.rhs > TOL_MM:
                return math.inf, -math.inf, (p.label,)
            continue
        (lows if coeff > 0 else highs).append((p.rhs/coeff, p.label))
    low, high = max(lows), min(highs)
    return low[0], high[0], (low[1], high[1])


def hardware_violations(state: AppState):
    g = state.geometry
    return tuple(f"{p.label}: short by {-p.residual(g.a_mm, g.b_mm):.3f} mm" for p in physical_constraints(state)
                 if p.residual(g.a_mm, g.b_mm) < -TOL_MM)


def _intersection(p, q):
    det = p.ca*q.cb - q.ca*p.cb
    if det == 0:
        return None
    return ((p.rhs*q.cb-q.rhs*p.cb)/det, (p.ca*q.rhs-q.ca*p.rhs)/det)


def _closure_feasible(a, b, planes):
    return math.isfinite(a) and math.isfinite(b) and all(p.residual(a, b) >= -TOL_MM*max(1, abs(p.ca), abs(p.cb)) for p in planes)


def _attained(a, b, planes):
    return a > 0 and b > 0 and all(not p.open or p.residual(a, b) > 1e-10 for p in planes)


def solve(state: AppState) -> FeasibilityResult:
    state.validate()
    req, d, angle = state.requirements, state.profile.detector, state.angle
    base = calculate(state.geometry, d)
    wx, wy = base.crop_scintillator_x_mm, base.crop_scintillator_y_mm
    lx = None if req.fov_x_mm is None else req.fov_x_mm+2*req.margin_mm
    ly = None if req.fov_y_mm is None else req.fov_y_mm+2*req.margin_mm
    m_upper = min(wx/lx if lx else math.inf, wy/ly if ly else math.inf)
    m_pixel = d.binning*d.pitch_um/(d.optical_m*req.sampling_um) if req.sampling_um else 1.0
    m_lower = max(1.0, m_pixel)
    exact = req.sampling_um is not None and req.sampling_mode == "exact"
    if exact:
        if m_pixel <= 1:
            return FeasibilityResult("infeasible", f"Exact sampling requires M_g = {m_pixel:.9g}. Positive a and b require M_g > 1; M_g = 1 is the b = 0 limiting family.")
        m_lower = m_pixel
    if m_upper <= 1 or m_lower > m_upper + ALGEBRA_TOL:
        counts = (required_crop(lx, req.sampling_um)[0] if lx and req.sampling_um else None,
                  required_crop(ly, req.sampling_um)[0] if ly and req.sampling_um else None)
        msg = f"Imaging requirements do not overlap: M_g ≥ {m_lower:.9g}, coverage requires M_g ≤ {m_upper:.9g}."
        if counts[0] is not None:
            msg += f" Requested {lx:g} mm at {req.sampling_um:g} µm needs {counts[0]} pixels across; {base.crop_nx} are available."
            msg += f" At this sampling the acquired width is {base.crop_nx*req.sampling_um/1000:g} mm."
        msg += " Choose coarser sampling, a smaller field, another calibrated configuration, or separately plan multi-acquisition stitching. Binning and interpolation do not add acquired pixels."
        return FeasibilityResult("infeasible", msg, magnification_interval=(m_lower, m_upper), required_crop_pixels=counts)
    if exact:
        m_upper = m_lower
    if state.profile.objectives[state.profile.selected_objective].availability == "unavailable":
        return FeasibilityResult("infeasible", "Selected objective is marked unavailable in the instrument profile.")
    ew, eh = (base.scintillator_x_mm, base.scintillator_y_mm) if angle.envelope == "active" else (wx, wy)
    boundary = angle_distance_min(ew, eh, angle)
    buffered = angle_distance_min(ew, eh, angle, buffered=True)
    planes = [HalfPlane(1, 0, 0, "positive source distance", True), HalfPlane(0, 1, 0, "positive detector distance", True)]
    from .projection import x_extent, phantom_points
    min_x, max_x = x_extent(state.phantom)
    if state.phantom.roi_enabled:
        roi_points = phantom_points(state.phantom, roi=True)
        min_x, max_x = min(min_x, float(roi_points[:, 0].min())), max(max_x, float(roi_points[:, 0].max()))
    planes += [HalfPlane(1, 0, -min_x, "specimen in front of source", True),
               HalfPlane(0, 1, max_x, "specimen before scintillator", True)]
    planes += physical_constraints(state)
    planes.append(HalfPlane(-(m_lower-1), 1, 0, "sampling lower magnification"))
    if math.isfinite(m_upper):
        planes.append(HalfPlane(m_upper-1, -1, 0, "coverage upper magnification"))
    if buffered is not None:
        planes.append(HalfPlane(1, 1, buffered, "buffered acquisition angle", angle.strict and angle.buffer_deg == 0))
    if req.fixed_kind != "none":
        ca, cb = {"a": (1, 0), "b": (0, 1), "D": (1, 1)}[req.fixed_kind]
        planes += [HalfPlane(ca, cb, req.fixed_mm, f"fixed {req.fixed_kind}"), HalfPlane(-ca, -cb, -req.fixed_mm, f"fixed {req.fixed_kind}")]
    points = []
    for i, p in enumerate(planes):
        for q in planes[i+1:]:
            point = _intersection(p, q)
            if point and _closure_feasible(*point, planes):
                points.append(point)
    current = (state.geometry.a_mm, state.geometry.b_mm)
    if _closure_feasible(*current, planes):
        points.append(current)
    if req.goal == "closest to current distances":
        for p in planes:
            norm = p.ca*p.ca+p.cb*p.cb
            if norm:
                step = p.residual(*current)/norm
                point = current[0]-step*p.ca, current[1]-step*p.cb
                if _closure_feasible(*point, planes):
                    points.append(point)
    interval = source_interval(m_lower, planes) if exact else None
    if not points:
        labels = interval[2] if interval else tuple(p.label for p in planes[2:])
        return FeasibilityResult("infeasible", "No distance pair satisfies all constraints. Conflicts: " + "; ".join(labels),
            magnification_interval=(m_lower, m_upper), source_interval_mm=interval[:2] if interval else None,
            angle_equality_D_mm=boundary, angle_buffered_D_mm=buffered, active_constraints=labels)
    distance2 = lambda p: (p[0]-current[0])**2+(p[1]-current[1])**2
    if req.goal == "minimum separation":
        min_D = min(a+b for a, b in points)
        candidates = [p for p in points if abs(sum(p)-min_D) <= TOL_MM]
        # Finite upper imaging magnification wins on a constant-D edge.
        candidates.sort(key=lambda p: (-((p[0]+p[1])/p[0] if p[0] > 0 else math.inf), distance2(p)))
    else:
        candidates = sorted(points, key=distance2)
    a, b = candidates[0]
    if not _attained(a, b, planes):
        return FeasibilityResult("family", "The best separation is an unattained boundary of positive distances or a strict angle. Choose a fixed separation/source/detector distance, a positive angular buffer, or configure a physical lower bound. No epsilon distance has been invented.",
            magnification_interval=(m_lower, m_upper), source_interval_mm=interval[:2] if interval else None,
            angle_equality_D_mm=boundary, angle_buffered_D_mm=buffered)
    candidate = GeometryInputs(a, b)
    results = calculate(candidate, d)
    # A strict original limit with a positive buffer permits equality at the
    # buffered recommendation. With no buffer the open-boundary rule above applies.
    pixels, coverage = [], []
    for length in (lx, ly):
        pair = required_crop(length, results.sampling_um) if length else (None, None)
        pixels.append(pair[0]); coverage.append(pair[1])
    active = tuple(p.label for p in planes if abs(p.residual(a, b)) < TOL_MM)
    reason = f"{req.goal.capitalize()}: a = {a:.9g} mm, b = {b:.9g} mm, D = {a+b:.9g} mm. Distance family b = {results.geometrical_m-1:.9g} a."
    if boundary:
        reason += f" Angle equality D = {boundary:.9g} mm; buffered boundary D = {buffered:.9g} mm ({angle.buffer_deg:g}° in {angle.convention} convention)."
    reason += " Active: " + ", ".join(active) + ". Geometry does not predict exposure time or SNR."
    return FeasibilityResult("feasible", reason, candidate, (m_lower, m_upper), interval[:2] if interval else None,
        boundary, buffered, active, tuple(pixels), tuple(coverage))
