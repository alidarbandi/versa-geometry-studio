"""Perspective rays, exact simple-phantom extents, and finite segment intersections."""
from dataclasses import dataclass, replace
import math
import numpy as np
from .models import GeometryInputs, DetectorProfile, Phantom, finite
from .physics import calculate


def rotation_matrix(degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def center(ph):
    return np.array([ph.offset_x_mm, ph.offset_y_mm, ph.offset_z_mm])


def radii(ph):
    return np.array([ph.depth_mm, ph.width_mm, ph.height_mm])/2


def world_points(local, ph):
    return np.asarray(local) @ rotation_matrix(ph.rotation_deg).T + center(ph)


def local_points(world, ph):
    return (np.asarray(world)-center(ph)) @ rotation_matrix(ph.rotation_deg)


def phantom_points(ph: Phantom, roi=False):
    if roi or ph.shape == "cuboid":
        r = np.array([ph.roi_depth_mm, ph.roi_width_mm, ph.roi_height_mm])/2 if roi else radii(ph)
        pts = np.array([(x, y, z) for x in (-r[0], r[0]) for y in (-r[1], r[1]) for z in (-r[2], r[2])])
        if roi:
            pts += np.array([ph.roi_offset_x_mm, ph.roi_offset_y_mm, ph.roi_offset_z_mm])
    else:
        u, v = np.meshgrid(np.linspace(0, 2*math.pi, 65), np.linspace(-math.pi/2, math.pi/2, 33))
        pts = np.stack([np.cos(v)*np.cos(u), np.cos(v)*np.sin(u), np.sin(v)], axis=-1).reshape(-1, 3)*radii(ph)
    return world_points(pts, ph)


def x_extent(ph):
    r, rot = radii(ph), rotation_matrix(ph.rotation_deg)
    half = np.linalg.norm(rot[0]*r) if ph.shape == "ellipsoid" else np.abs(rot[0]*r).sum()
    return ph.offset_x_mm-half, ph.offset_x_mm+half


def validate_placement(g, ph):
    ph.validate()
    low, high = x_extent(ph)
    if low <= -g.a_mm:
        raise ValueError("Specimen intersects or lies behind the source plane: require a + x > 0 for every point")
    if high >= g.b_mm:
        raise ValueError("Specimen intersects or lies beyond the scintillator plane")
    if ph.roi_enabled:
        roi = phantom_points(ph, roi=True)
        if roi[:, 0].min() <= -g.a_mm or roi[:, 0].max() >= g.b_mm:
            raise ValueError("Target ROI must lie between source and scintillator planes")


def project_points(points, g: GeometryInputs):
    g.validate()
    pts = np.asarray(points, dtype=float)
    if pts.shape[-1] != 3 or not np.all(np.isfinite(pts)):
        raise ValueError("Object points must be finite (x,y,z) in mm")
    denominator = g.a_mm+pts[..., 0]
    if np.any(denominator <= 0):
        raise ValueError("Point projection requires a + x > 0")
    factors = (g.a_mm+g.b_mm)/denominator
    return pts[..., 1:]*factors[..., None], factors


@dataclass(frozen=True)
class PointProjection:
    point_mm: tuple[float, float, float]
    magnification: float
    scintillator_mm: tuple[float, float, float]
    camera_yz_mm: tuple[float, float]
    pixel_uv: tuple[float, float]
    crop_pixel_uv: tuple[float, float]
    clipped_active: bool
    clipped_crop: bool


def inspect_point(point, g, d):
    r = calculate(g, d)
    yz, factors = project_points(np.array(point, dtype=float), g)
    parity = np.array([-1 if d.flip_y else 1, -1 if d.flip_z else 1])
    camera = yz*d.optical_m*parity
    pitch = d.binning*d.pitch_um/1000
    uv = camera/pitch + (np.array([r.output_nx, r.output_ny])-1)/2
    crop_uv = camera/pitch + (np.array([r.crop_nx, r.crop_ny])-1)/2
    return PointProjection(tuple(point), float(factors), (g.b_mm, *yz), tuple(camera), tuple(uv), tuple(crop_uv),
        bool(abs(yz[0]) > r.scintillator_x_mm/2+1e-9 or abs(yz[1]) > r.scintillator_y_mm/2+1e-9),
        bool(abs(yz[0]) > r.crop_scintillator_x_mm/2+1e-9 or abs(yz[1]) > r.crop_scintillator_y_mm/2+1e-9))


def projected_extents(g, ph, roi=False):
    """Exact extrema for a cuboid (vertices), or an ellipsoid (tangent rays).

    Returns detector y_min,y_max,z_min,z_max, not center-plane dimensions.
    """
    validate_placement(g, ph)
    if roi or ph.shape == "cuboid":
        projected, _ = project_points(phantom_points(ph, roi), g)
        return (float(projected[:, 0].min()), float(projected[:, 0].max()),
                float(projected[:, 1].min()), float(projected[:, 1].max()))
    R = rotation_matrix(ph.rotation_deg)
    Q = R @ np.diag(radii(ph)**2) @ R.T
    c, A, D = center(ph), g.a_mm+ph.offset_x_mm, g.a_mm+g.b_mm
    vals = []
    for axis in (1, 2):
        coeff = (A*A-Q[0, 0], -2*A*c[axis]+2*Q[0, axis], c[axis]**2-Q[axis, axis])
        roots = np.sort(np.roots(coeff).real)*D
        vals.extend(roots.tolist())
    return tuple(vals)


def coverage(g, d, ph, roi=False):
    bounds = projected_extents(g, ph, roi)
    r = calculate(g, d)
    half_x, half_y = r.crop_scintillator_x_mm/2, r.crop_scintillator_y_mm/2
    severity = max(-bounds[0]/half_x, bounds[1]/half_x, -bounds[2]/half_y, bounds[3]/half_y)
    return {"bounds_scintillator_mm": bounds, "extent_scintillator_mm": (bounds[1]-bounds[0], bounds[3]-bounds[2]),
            "equivalent_center_extent_mm": ((bounds[1]-bounds[0])/r.geometrical_m, (bounds[3]-bounds[2])/r.geometrical_m),
            "clipped": bool(severity > 1+1e-9), "edge_ratio": severity}


def sweep_coverage(g, d, ph, increment_deg=5.0):
    finite(increment_deg, "Sweep increment (degrees)", True)
    if increment_deg > 90:
        raise ValueError("Sweep increment must be at most 90°")
    rows = []
    def sample(angle):
        p = replace(ph, rotation_deg=float(angle % 360))
        full = coverage(g, d, p)
        roi = coverage(g, d, p, True) if ph.roi_enabled else None
        rows.append((float(angle % 360), full, roi))
    for angle in np.arange(0, 360, increment_deg):
        sample(angle)
    worst = max(rows, key=lambda x: x[1]["edge_ratio"])[0]
    for angle in np.arange(worst-increment_deg, worst+increment_deg, increment_deg/10):
        sample(angle)
    worst_row = max(rows, key=lambda x: x[1]["edge_ratio"])
    return {"assessment": "sampled full-rotation coverage; not a rigorous continuous-angle guarantee",
        "increment_deg": increment_deg, "local_refinement_deg": increment_deg/10, "samples": len(rows),
        "worst_angle_deg": worst_row[0], "specimen_clipped": any(r[1]["clipped"] for r in rows),
        "roi_clipped": any(r[2]["clipped"] for r in rows) if ph.roi_enabled else None,
        "max_equivalent_center_extent_mm": tuple(max(r[1]["equivalent_center_extent_mm"][i] for r in rows) for i in (0, 1))}


def inclusion_specs(ph):
    """Disjoint spherical inclusions, completely contained in either phantom."""
    r = radii(ph)
    # The smallest normalized center separation is sqrt(.15²+.43²+.14²)
    # = .477. A diameter .44*min(r) stays disjoint for every aspect ratio.
    radius = float(min(r)*0.22)
    fractions = ((0.0, -0.38, 0.24), (0.12, 0.32, -0.25), (-0.15, 0.05, 0.38))
    return [(np.array(f)*r, radius) for f in fractions]


def marker_points(ph):
    return world_points(np.array([p for p, _ in inclusion_specs(ph)]), ph)


def ray_interval(origin, directions, shape, half_sizes, max_distance):
    """Analytic intersections of finite, unit-direction segments in local space.

    Broadcasting supports arrays of rays; outputs entry/exit lengths in mm.
    Misses have exit == entry == 0. Zero slab directions are handled explicitly.
    """
    o, v, r = np.asarray(origin), np.asarray(directions), np.asarray(half_sizes)
    if shape == "cuboid":
        parallel = np.abs(v) < 1e-14
        safe = np.where(parallel, 1.0, v)
        t0, t1 = (-r-o)/safe, (r-o)/safe
        low = np.where(parallel, -np.inf, np.minimum(t0, t1))
        high = np.where(parallel, np.inf, np.maximum(t0, t1))
        miss = np.any(parallel & (np.abs(o) > r), axis=-1)
        entry, exit = np.max(low, axis=-1), np.min(high, axis=-1)
    elif shape == "ellipsoid":
        ov, vv = o/r, v/r
        aa, bb = np.sum(vv*vv, axis=-1), 2*np.sum(ov*vv, axis=-1)
        cc = np.sum(ov*ov, axis=-1)-1
        discr = bb*bb-4*aa*cc
        miss = discr < 0
        root = np.sqrt(np.maximum(discr, 0))
        entry, exit = (-bb-root)/(2*aa), (-bb+root)/(2*aa)
    else:
        raise ValueError("Unsupported intersection shape")
    entry, exit = np.maximum(entry, 0), np.minimum(exit, max_distance)
    miss = miss | (exit <= entry)
    return np.where(miss, 0, entry), np.where(miss, 0, exit)


def ray_path_lengths(g, ph, detector_yz):
    target = np.concatenate([np.full((*detector_yz.shape[:-1], 1), g.b_mm), detector_yz], axis=-1)
    source = np.array([-g.a_mm, 0, 0])
    delta = target-source
    distance = np.linalg.norm(delta, axis=-1)
    directions = delta/distance[..., None]
    R = rotation_matrix(ph.rotation_deg)
    origin_local = (source-center(ph)) @ R
    directions_local = directions @ R
    enter, leave = ray_interval(origin_local, directions_local, ph.shape, radii(ph), distance)
    base_length = leave-enter
    inclusion_length = np.zeros_like(base_length)
    for pos, radius in inclusion_specs(ph):
        inc_enter, inc_leave = ray_interval(origin_local-pos, directions_local, "ellipsoid", np.full(3, radius), distance)
        # Explicitly restrict inclusions to host intervals for robustness.
        inclusion_length += np.maximum(0, np.minimum(leave, inc_leave)-np.maximum(enter, inc_enter))
    return base_length, inclusion_length

