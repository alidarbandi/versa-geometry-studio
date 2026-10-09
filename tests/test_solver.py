from dataclasses import replace
import math
import pytest
from versa_geometry_studio.models import (AppState, AngleConstraint, Quantity, CoordinateMapping, GeometryInputs)
from versa_geometry_studio.physics import calculate, angle_passes
from versa_geometry_studio.solver import solve, source_interval, HalfPlane, hardware_violations


def test_default_minimum_and_buffer():
    state=AppState()
    out=solve(state)
    assert out.status=='feasible'
    assert out.angle_equality_D_mm==pytest.approx(465.016662669,abs=1e-6)
    assert sum((out.candidate.a_mm,out.candidate.b_mm))==pytest.approx(out.angle_buffered_D_mm)
    r=calculate(out.candidate,state.profile.detector)
    assert r.selected_angle_deg(state.angle)==pytest.approx(11.98)
    assert r.sampling_um==pytest.approx(14.6484375)
    assert angle_passes(r,state.angle)


def test_3000_pixels_are_infeasible():
    s=AppState(); s=replace(s,requirements=replace(s.requirements,sampling_um=10))
    result=solve(s)
    assert result.status=='infeasible' and result.candidate is None
    assert '3000 pixels' in result.explanation and '2048' in result.explanation
    s=replace(s,requirements=replace(s.requirements,fov_x_mm=None,fov_y_mm=None))
    out=solve(s); r=calculate(out.candidate,s.profile.detector)
    assert r.geometrical_m==pytest.approx(3.375)
    assert r.fov_x_mm==pytest.approx(20.48)


def test_interval_and_conflicting_physical_bounds():
    low,high,_=source_interval(2,[HalfPlane(1,0,10,'a_min'),HalfPlane(0,-1,-20,'b_max'),HalfPlane(1,1,30,'D_min')])
    assert low==15 and high==20
    s=AppState(); profile=replace(s.profile,bounds={'a_min':Quantity(400,confirmed=True),'D_max':Quantity(500,confirmed=True)})
    out=solve(replace(s,profile=profile))
    assert out.status=='infeasible'
    assert out.source_interval_mm[0]>out.source_interval_mm[1]


def test_unconfirmed_limits_do_not_constrain():
    s=AppState(); profile=replace(s.profile,bounds={'D_max':Quantity(1,confirmed=False)})
    assert solve(replace(s,profile=profile)).status=='feasible'
    assert solve(replace(s,profile=replace(profile,bounds={'D_max':Quantity(1,confirmed=True)}))).status=='infeasible'


def test_legacy_mapping_requires_both_confirmation_and_calibration():
    s=AppState(); angle=replace(s.angle,limit_deg=None)
    req=replace(s.requirements,fixed_kind='D',fixed_mm=150)
    profile=replace(s.profile,legacy_stage_min=replace(s.profile.legacy_stage_min,value=200,confirmed=True))
    assert solve(replace(s,profile=profile,angle=angle,requirements=req)).status=='feasible'
    mapping=CoordinateMapping(True,1,1,0,'synthetic mapping for unit test only')
    out=solve(replace(s,profile=replace(profile,mapping=mapping),angle=angle,requirements=req))
    assert out.status=='infeasible'


def test_conventions_change_solver_immediately():
    s=AppState()
    full=solve(s)
    half=solve(replace(s,angle=replace(s.angle,convention='half')))
    vertical=solve(replace(s,angle=replace(s.angle,axis='vertical')))
    assert half.angle_equality_D_mm<vertical.angle_equality_D_mm<full.angle_equality_D_mm


def test_open_boundary_no_invented_epsilon():
    s=AppState()
    no_angle=replace(s,angle=replace(s.angle,limit_deg=None))
    assert solve(no_angle).status=='family'
    assert solve(replace(s,angle=replace(s.angle,buffer_deg=0))).status=='family'
    one=replace(s,requirements=replace(s.requirements,sampling_um=33.75,fov_x_mm=None,fov_y_mm=None))
    assert solve(one).status=='infeasible'


def test_closest_goal_and_fixed_distances():
    s=AppState()
    close=solve(replace(s,requirements=replace(s.requirements,goal='closest to current distances')))
    assert close.candidate==s.geometry
    for key, value in (('a',220),('b',300),('D',600)):
        out=solve(replace(s,requirements=replace(s.requirements,fixed_kind=key,fixed_mm=value)))
        r=calculate(out.candidate,s.profile.detector)
        assert {'a':r.a_mm,'b':r.b_mm,'D':r.D_mm}[key]==pytest.approx(value)


def test_no_coarser_tie_prefers_finest_sampling_with_coverage():
    s=AppState(); req=replace(s.requirements,sampling_um=20,sampling_mode='no coarser')
    out=solve(replace(s,requirements=req))
    r=calculate(out.candidate,s.profile.detector)
    assert r.geometrical_m==pytest.approx(2.304)
    assert r.sampling_um==pytest.approx(14.6484375)


def test_confirmed_clearance_includes_sample_surface():
    s=AppState(); p=replace(s.profile,bounds={'source_clearance':Quantity(210,confirmed=True)})
    out=solve(replace(s,profile=p))
    assert out.candidate.a_mm>=210+math.hypot(28,5)/2-1e-8
    assert hardware_violations(replace(s,profile=p))
