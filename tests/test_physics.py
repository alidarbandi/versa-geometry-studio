from dataclasses import replace
import math
import pytest
from versa_geometry_studio.models import DetectorProfile, GeometryInputs, AngleConstraint
from versa_geometry_studio.physics import (calculate, angle_distance_min, angle_passes,
    distances_at_separation, required_crop, effective_optical_factor, penumbra_um)


@pytest.mark.parametrize("a,b,D,mg,fov,sampling", [
    (65.1041666667, 84.8958333333, 150, 2.304, 30, 14.6484375),
    (72, 78, 150, 2.0833333333, 33.1776, 16.2),
    (150, 195.6, 345.6, 2.304, 30, 14.6484375),
    (205, 267.32, 472.32, 2.304, 30, 14.6484375),
])
def test_reference_geometry(a,b,D,mg,fov,sampling):
    r = calculate(GeometryInputs(a,b), DetectorProfile())
    assert r.D_mm == pytest.approx(D, rel=1e-9)
    assert r.geometrical_m == pytest.approx(mg, rel=1e-9)
    assert r.fov_x_mm == pytest.approx(fov, rel=1e-9)
    assert r.sampling_um == pytest.approx(sampling, rel=1e-9)


def test_camera_is_not_scintillator():
    r = calculate(GeometryInputs(), DetectorProfile())
    assert r.camera_x_mm == pytest.approx(27.648)
    assert r.scintillator_x_mm == pytest.approx(69.12)
    assert r.total_m == pytest.approx(.9216)


@pytest.mark.parametrize("a,b,h,d", [(150,195.6,11.421186275,16.098933951),(205,267.32,8.369832250,11.815770331)])
def test_reference_angles(a,b,h,d):
    r = calculate(GeometryInputs(a,b), DetectorProfile())
    full = r.angles_deg(AngleConstraint())
    assert full == pytest.approx((h,h,d), abs=1e-6)


@pytest.mark.parametrize("axis,convention,D", [
    ("vertical","full",328.816435538),("diagonal","full",465.016662669),
    ("horizontal","half",162.592016584),("diagonal","half",229.939834986)])
def test_equality_boundaries(axis,convention,D):
    c = AngleConstraint(axis=axis,convention=convention)
    boundary = angle_distance_min(69.12,69.12,c)
    assert boundary == pytest.approx(D,abs=1e-6)
    r = calculate(distances_at_separation(2.304,boundary),DetectorProfile())
    assert not angle_passes(r,c)
    assert angle_passes(r,replace(c,strict=False))


def test_binning_crop_and_scaling_invariants():
    d, g = DetectorProfile(), GeometryInputs()
    r = calculate(g,d)
    binned = calculate(g,replace(d,binning=2))
    cropped = calculate(g,replace(d,crop_nx=1024,crop_ny=1024))
    assert (binned.output_nx,binned.output_ny)==(1024,1024)
    assert binned.fov_x_mm==pytest.approx(30)
    assert binned.sampling_um==pytest.approx(29.296875)
    assert cropped.crop_fov_x_mm==pytest.approx(15)
    assert cropped.sampling_um==r.sampling_um
    scaled = calculate(GeometryInputs(g.a_mm*2,g.b_mm*2),d)
    assert scaled.geometrical_m==r.geometrical_m
    assert scaled.sampling_um==r.sampling_um
    assert all(x<y for x,y in zip(scaled.half_angles_rad,r.half_angles_rad))


def test_independent_distance_changes():
    d, g = DetectorProfile(), GeometryInputs()
    r=calculate(g,d)
    rb=calculate(replace(g,b_mm=g.b_mm+50),d)
    ra=calculate(replace(g,a_mm=g.a_mm+50),d)
    assert rb.geometrical_m>r.geometrical_m and rb.sampling_um<r.sampling_um and rb.fov_x_mm<r.fov_x_mm
    assert ra.geometrical_m<r.geometrical_m and ra.sampling_um>r.sampling_um and ra.fov_x_mm>r.fov_x_mm
    assert rb.half_angles_rad[2]<r.half_angles_rad[2] and ra.half_angles_rad[2]<r.half_angles_rad[2]


def test_usable_rectangle_and_circle():
    d=DetectorProfile(usable_nx=1600,usable_ny=1200,image_circle_mm=50)
    r=calculate(GeometryInputs(),d)
    assert math.hypot(r.scintillator_x_mm,r.scintillator_y_mm)<=50+1e-9
    assert r.output_nx<1600 and r.output_ny<1200
    assert required_crop(30,14.6484375)==(2048,30)
    count, length=required_crop(30.001,14.6484375)
    assert count==2049 and length>=30.001


@pytest.mark.parametrize("g", [GeometryInputs(0,1),GeometryInputs(-1,1),GeometryInputs(float('nan'),1),GeometryInputs(1,float('inf'))])
def test_invalid_distances(g):
    with pytest.raises(ValueError): calculate(g,DetectorProfile())


@pytest.mark.parametrize("d", [DetectorProfile(nx=3,binning=2),DetectorProfile(crop_nx=3000),DetectorProfile(optical_m=0),DetectorProfile(usable_nx=0),DetectorProfile(binning=3)])
def test_invalid_detector(d):
    with pytest.raises(ValueError): calculate(GeometryInputs(),d)


@pytest.mark.parametrize("c", [AngleConstraint(limit_deg=0),AngleConstraint(limit_deg=180),AngleConstraint(limit_deg=float('nan')),AngleConstraint(buffer_deg=-1),AngleConstraint(convention='bad')])
def test_invalid_angles(c):
    with pytest.raises(ValueError): c.validate()


def test_limit_one_and_calibration():
    with pytest.raises(ValueError,match="limiting family"):
        distances_at_separation(1,150)
    near=distances_at_separation(1+1e-8,150)
    assert near.b_mm>0
    assert effective_optical_factor(GeometryInputs(),13.5,1,14.6484375)==pytest.approx(.4)
    assert penumbra_um(2,2)==1

