"""Vectorized, deterministic transmission preview, independent of Qt."""
from dataclasses import dataclass
import time
import numpy as np
from .physics import calculate
from .projection import validate_placement, ray_path_lengths


@dataclass(frozen=True)
class RenderResult:
    revision: int
    transmission: np.ndarray
    elapsed_ms: float


def render_projection(g, d, ph, resolution=256, revision=0):
    started = time.perf_counter()
    validate_placement(g, ph)
    if type(resolution) is not int or not 16 <= resolution <= 2048:
        raise ValueError("Preview resolution must be an integer from 16 to 2048")
    r = calculate(g, d)
    nx, ny = resolution, max(16, round(resolution*r.scintillator_y_mm/r.scintillator_x_mm))
    ny = min(ny, 2048)
    # Sample preview pixel centers on the full active rectangle. Display vertical
    # direction is downward; physical z and reported v remain upward.
    y = ((np.arange(nx)+0.5)/nx-0.5)*r.scintillator_x_mm
    z = (0.5-(np.arange(ny)+0.5)/ny)*r.scintillator_y_mm
    if d.flip_y:
        y = -y
    if d.flip_z:
        z = -z
    yy, zz = np.meshgrid(y, z)
    lengths, inc_lengths = ray_path_lengths(g, ph, np.stack([yy, zz], axis=-1))
    # Background + inclusion difference replaces host attenuation; no double count.
    tau = ph.mu_mm_inv*lengths + (ph.inclusion_mu_mm_inv-ph.mu_mm_inv)*inc_lengths
    transmission = np.exp(-np.maximum(tau, 0)).astype(np.float32)
    return RenderResult(revision, transmission, (time.perf_counter()-started)*1000)
