"""Versioned JSON, recomputed results, provenance, and portable planning exports."""
from __future__ import annotations
from dataclasses import asdict, replace
from pathlib import Path
import csv
import io
import json
import math
import os
import tempfile
from .models import (AppState, AngleConstraint, CoordinateMapping, DetectorProfile, GeometryInputs,
                     ImagingRequirements, InstrumentProfile, ObjectiveCalibration, Phantom, Quantity)
from .physics import calculate
from .projection import coverage, validate_placement
from .solver import solve, hardware_violations

SCHEMA_VERSION = 1
UNITS = {"geometry": "mm", "trigonometry": "rad", "display_angles": "degrees",
         "pitch_um": "µm", "sampling_um": "µm/pixel", "attenuation": "mm^-1",
         "optical_m": "dimensionless", "counts": "pixels", "rotation_deg": "degrees"}


def _quantity_dict(data):
    return {key: Quantity(**value) for key, value in data.items()}


def detector_from_dict(data):
    data = dict(data)
    if "provenance" in data:
        data["provenance"] = _quantity_dict(data["provenance"])
    return DetectorProfile(**data)


def profile_from_dict(data):
    data = dict(data)
    objectives = {}
    for key, raw in data.pop("objectives").items():
        raw = dict(raw)
        raw["detector"] = detector_from_dict(raw["detector"])
        raw["bounds"] = _quantity_dict(raw.get("bounds", {}))
        objectives[key] = ObjectiveCalibration(**raw)
    data["objectives"] = objectives
    data["bounds"] = _quantity_dict(data.get("bounds", {}))
    data["mapping"] = CoordinateMapping(**data.get("mapping", {}))
    for key in ("legacy_stage_min", "focal_spot_um"):
        if key in data:
            data[key] = Quantity(**data[key])
    profile = InstrumentProfile(**data)
    profile.validate()
    return profile


def state_from_dict(data):
    data = dict(data)
    data["profile"] = profile_from_dict(data["profile"])
    for key, cls in (("geometry", GeometryInputs), ("requirements", ImagingRequirements), ("angle", AngleConstraint), ("phantom", Phantom)):
        data[key] = cls(**data[key])
    state = AppState(**data)
    state.validate()
    validate_placement(state.geometry, state.phantom)
    return state


def plan_document(state):
    state.validate()
    validate_placement(state.geometry, state.phantom)
    return {"format": "versa-geometry-plan", "schema_version": SCHEMA_VERSION, "units": dict(UNITS),
            "state": asdict(state), "computed_results": asdict(calculate(state.geometry, state.profile.detector))}


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name+".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_plan(path, state):
    atomic_text(path, json.dumps(plan_document(state), ensure_ascii=False, indent=2, allow_nan=False))


def _equal_saved(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal_saved(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(_equal_saved(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-10)
    return a == b


def read_json(path):
    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")
    with open(path, encoding="utf-8-sig") as stream:
        return json.load(stream, parse_constant=reject_constant)


def load_plan(path):
    raw = read_json(path)
    if raw.get("format") != "versa-geometry-plan" or raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported acquisition plan format/version")
    if raw.get("units") != UNITS:
        raise ValueError("Plan units are missing or incompatible; no implicit unit conversion is performed")
    try:
        state = state_from_dict(raw["state"])
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError(f"Malformed plan: {exc}") from exc
    actual = asdict(calculate(state.geometry, state.profile.detector))
    warnings = []
    if not _equal_saved(actual, raw.get("computed_results")):
        warnings.append("Saved derived results differ from the authoritative calculation; results were recomputed.")
    return state, warnings


def save_profile(path, profile):
    profile.validate()
    atomic_text(path, json.dumps({"format": "versa-instrument-profile", "schema_version": SCHEMA_VERSION,
                                "profile": asdict(profile)}, indent=2, ensure_ascii=False, allow_nan=False))


def load_profile(path):
    raw = read_json(path)
    if raw.get("format") != "versa-instrument-profile" or raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported profile format/version")
    try:
        return profile_from_dict(raw["profile"])
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError(f"Malformed profile: {exc}") from exc


def parameter_rows(state):
    r, d = calculate(state.geometry, state.profile.detector), state.profile.detector
    rows = []
    def add(name, value, units, role):
        rows.append((name, value, units, role))
    for name, value in asdict(r).items():
        units = "rad" if name.endswith("rad") else "µm/pixel" if name == "sampling_um" else "mm" if name.endswith("mm") else "pixels" if name.endswith(("nx", "ny")) else "dimensionless"
        if isinstance(value, tuple):
            for axis, v in zip(("horizontal", "vertical", "diagonal"), value):
                add(name+"."+axis, v, units, "derived")
                add(name.replace("half_angles_rad", "full_angles_deg")+"."+axis, math.degrees(v)*2, "degrees", "derived")
        else:
            add(name, value, units, "derived")
    for section, model in (("detector", d), ("requirements", state.requirements), ("angle", state.angle), ("phantom", state.phantom)):
        for name, value in asdict(model).items():
            if isinstance(value, dict):
                continue
            units = "mm^-1" if name.endswith("mm_inv") else "mm" if name.endswith("mm") else "µm" if name.endswith("um") else "degrees" if name.endswith("deg") else "pixels" if name in ("nx", "ny", "usable_nx", "usable_ny", "crop_nx", "crop_ny") else "dimensionless"
            add(section+"."+name, "unconfigured" if value is None else value, units, "input")
    for scope, bounds in (("profile", state.profile.bounds), ("objective", state.profile.objectives[state.profile.selected_objective].bounds)):
        for name, q in bounds.items():
            add(scope+"."+name, "unconfigured" if q.value is None else q.value, q.units, f"{q.origin}; confirmed={q.confirmed}; {q.source} {q.version} {q.date}")
    add("profile.name", state.profile.name, "text", "input")
    add("profile.objective", state.profile.selected_objective, "text", "input")
    add("profile.legacy_stage_min", state.profile.legacy_stage_min.value, "mm", "legacy reference, stage coordinates; confirmed="+str(state.profile.legacy_stage_min.confirmed))
    add("profile.mapping_verified", state.profile.mapping.verified, "dimensionless", "calibration")
    add("mode", state.mode, "text", "input")
    return rows


def parameter_csv(state, delimiter=","):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(("parameter", "value", "units", "role / provenance"))
    writer.writerows(parameter_rows(state))
    return buffer.getvalue()


def export_parameters(path, state):
    if Path(path).suffix.lower() == ".json":
        data = {"units": UNITS, "parameters": [dict(zip(("parameter", "value", "units", "role"), r)) for r in parameter_rows(state)], "plan": plan_document(state)}
        atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        atomic_text(path, parameter_csv(state))


def planning_summary(state):
    from .models import MANUAL, WHITEPAPER
    r, ph = calculate(state.geometry, state.profile.detector), state.phantom
    result = solve(state)
    cov = coverage(state.geometry, state.profile.detector, ph)
    lines = ["# Versa Geometry Studio — acquisition plan", "", f"Profile: {state.profile.name}",
        f"Objective: {state.profile.selected_objective} ({state.profile.objectives[state.profile.selected_objective].availability})", "",
        f"Source a = {r.a_mm!r} mm; scintillator b = {r.b_mm!r} mm; total D = {r.D_mm!r} mm.",
        f"Geometrical magnification = {r.geometrical_m!r}×; optical × geometrical = {r.total_m!r}×.",
        f"Acquired field = {r.crop_fov_x_mm!r} × {r.crop_fov_y_mm!r} mm at {r.sampling_um!r} µm/pixel.",
        f"Output = {r.crop_nx} × {r.crop_ny} binned pixels; full usable = {r.output_nx} × {r.output_ny}.",
        f"Angle convention: {state.angle.convention} {state.angle.axis}, {state.angle.envelope} envelope; limit = {state.angle.limit_deg} degrees, buffer = {state.angle.buffer_deg} degrees.", "",
        "## Equations and conventions", "",
        "M_g = (a+b)/a; M_total = m M_g; Δ = k p/(m M_g); FOV = N_out Δ.",
        "W = N_usable p/m; α = atan(R/D); full opening θ = 2α.",
        "Ray from S=(-a,0,0) through P=(x,y,z): t=(a+b)/(a+x); detector=(b,t y,t z).",
        "Geometry lengths are mm; p is converted from µm to mm; trigonometry uses radians.",
        "Pixel centers: u=y_camera/(k p)+(N_x,out−1)/2. Physical edges clip rays; displayed vertical axis is downward.",
        "Binning changes acquired sampling and count, not full usable FOV. Sampling is not measured spatial resolution.", "",
        "## Planning and coverage", "", f"Solver: {result.status}. {result.explanation}", result.tie_break,
        f"Current specimen clipping: {cov['clipped']}; equivalent center-plane projected extent = {cov['equivalent_center_extent_mm']} mm.",
        "Instantaneous coverage is separate from full-rotation coverage. A discrete sweep is a sampled assessment, not a guarantee.",
        "Synthetic transmission: I/I0 = exp(−μ_host ℓ_host − (μ_inclusion−μ_host) ℓ_inclusion), finite analytic ray intersections.",
        "This illustrative, noise-free monochromatic preview does not predict a calibrated ZEISS scan, exposure, SNR, or true resolution.", "",
        "## Constraints and calibration", "", state.profile.notes,
        "Confirmed hardware violations: " + ("; ".join(hardware_violations(state)) or "none among configured constraints"),
        "The legacy 135 mm rule is a stage-coordinate reference for 0.4× only. It is applied only after confirmation AND a verified signed affine coordinate mapping.",
        "Unconfigured travel, optical geometry, clearances, objective availability and source emission aperture are unknown. Sliders are model exploration ranges.", "",
        "## Parameters and provenance", "", "| Parameter | Value | Units | Role / provenance |", "|---|---|---|---|"]
    for row in parameter_rows(state):
        lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |")
    lines += ["", "Full profile provenance and coordinate mapping:", "", "```json", json.dumps(asdict(state.profile), ensure_ascii=False, indent=2), "```", "",
              f"[ZEISS legacy guide v11.x]({MANUAL}) (local confirmation required).", f"[ZEISS two-stage magnification technical note]({WHITEPAPER})."]
    if ph.roi_enabled:
        lines.insert(24, f"Current ROI clipping: {coverage(state.geometry, state.profile.detector, ph, True)['clipped']}; outer truncation is assessed separately.")
    return "\n".join(lines)+"\n"
