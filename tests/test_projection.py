from dataclasses import replace
import math
import numpy as np
import pytest
from versa_geometry_studio.models import GeometryInputs,DetectorProfile,Phantom
from versa_geometry_studio.projection import (project_points,inspect_point,projected_extents,
    phantom_points,coverage,sweep_coverage,ray_interval,ray_path_lengths,validate_placement,inclusion_specs,radii)
from versa_geometry_studio.renderer import render_projection


def test_perspective_centers_depth_and_edges():
    g,d=GeometryInputs(),DetectorProfile()
    center=inspect_point((0,1,2),g,d)
    near=inspect_point((-5,1,2),g,d)
    assert center.magnification==pytest.approx(2.304)
    assert center.scintillator_mm==(g.b_mm,pytest.approx(2.304),pytest.approx(4.608))
    assert near.magnification>center.magnification
    assert inspect_point((0,15,15),g,d).clipped_active is False
    assert inspect_point((0,15.001,0),g,d).clipped_active is True
    assert inspect_point((0,10,0),g,replace(d,crop_nx=1024)).clipped_crop
    zero=inspect_point((0,0,0),g,d)
    assert zero.pixel_uv==(1023.5,1023.5)
    with pytest.raises(ValueError,match=r'a \+ x'):
        project_points([[-205,1,1]],g)


def test_parity_only_changes_camera_mapping():
    g,d=GeometryInputs(),DetectorProfile()
    a=inspect_point((0,2,3),g,d)
    b=inspect_point((0,2,3),g,replace(d,flip_y=True,flip_z=True))
    assert a.scintillator_mm==b.scintillator_mm
    assert np.array(a.pixel_uv)+np.array(b.pixel_uv)==pytest.approx([2047,2047])


def test_ellipsoid_analytic_extents_contain_surface():
    ph=Phantom(shape='ellipsoid',rotation_deg=39,offset_y_mm=4)
    g=GeometryInputs()
    ext=projected_extents(g,ph)
    yz,_=project_points(phantom_points(ph),g)
    assert yz[:,0].min()>=ext[0]-1e-8 and yz[:,0].max()<=ext[1]+1e-8
    assert yz[:,1].min()>=ext[2]-1e-8 and yz[:,1].max()<=ext[3]+1e-8
    assert yz[:,0].min()-ext[0]<.06


def test_rotating_square_42_mm_and_interior_roi():
    ph=Phantom(width_mm=30,depth_mm=30,height_mm=5,rotation_deg=45,roi_enabled=True)
    g=GeometryInputs(1e9,1.304e9)
    extent=coverage(g,DetectorProfile(),ph)['equivalent_center_extent_mm'][0]
    assert extent==pytest.approx(42.42640687,abs=1e-6)
    assert coverage(g,DetectorProfile(),ph)['clipped']
    assert not coverage(g,DetectorProfile(),ph,True)['clipped']
    sweep=sweep_coverage(g,DetectorProfile(),ph,5)
    assert sweep['specimen_clipped'] and not sweep['roi_clipped']
    assert sweep['max_equivalent_center_extent_mm'][0]==pytest.approx(42.42640687,abs=1e-6)


@pytest.mark.parametrize('shape', ['cuboid','ellipsoid'])
def test_central_and_miss_ray_lengths(shape):
    origin=np.array([-10.,0,0]); dirs=np.array([[1.,0,0],[0.,1,0]])
    entry,exit=ray_interval(origin,dirs,shape,[2,3,4],30)
    assert exit-entry==pytest.approx([4,0])
    entry,exit=ray_interval(origin,dirs[:1],shape,[2,3,4],9)
    assert exit-entry==pytest.approx([1])


def test_transmission_and_inclusion_replacement_are_physical():
    g, d=GeometryInputs(),DetectorProfile(nx=256,ny=256,pitch_um=108)
    ph=Phantom(mu_mm_inv=.1,inclusion_mu_mm_inv=.1)
    host,inc=ray_path_lengths(g,ph,np.array([0.,0.]))
    assert host==pytest.approx(5)
    im=render_projection(g,d,ph,256)
    # Four rays nearest the center have essentially a five-mm slab path.
    assert im.transmission[127,127]==pytest.approx(math.exp(-.5),rel=1e-6)
    assert im.transmission[0,0]==1
    assert np.array_equal(im.transmission,render_projection(g,d,ph,256).transmission)
    lower=render_projection(g,d,replace(ph,inclusion_mu_mm_inv=0),256).transmission
    assert np.all(lower>=im.transmission-1e-7)
    rotated=render_projection(g,d,replace(ph,rotation_deg=90),256).transmission
    assert not np.array_equal(im.transmission,rotated)


def test_render_changes_with_geometry_and_optical_parity():
    g,d,ph=GeometryInputs(),DetectorProfile(),Phantom()
    a=render_projection(g,d,ph,128).transmission
    b=render_projection(replace(g,b_mm=350),d,ph,128).transmission
    assert not np.array_equal(a,b)
    flipped=render_projection(g,replace(d,flip_y=True,flip_z=True),ph,128).transmission
    np.testing.assert_allclose(flipped,a[::-1,::-1],atol=1e-7)


def test_impossible_placement():
    with pytest.raises(ValueError): validate_placement(GeometryInputs(1,1),Phantom())


@pytest.mark.parametrize('sizes',[(28,28,28),(1,1,100),(100,1,1),(1,100,1),(28,28,5)])
def test_inclusions_are_disjoint_and_contained_for_all_aspect_ratios(sizes):
    ph=Phantom(width_mm=sizes[0],height_mm=sizes[1],depth_mm=sizes[2])
    spheres=inclusion_specs(ph)
    for i,(position,radius) in enumerate(spheres):
        # A sufficient analytic containment bound in normalized ellipsoid space.
        assert np.linalg.norm(position/radii(ph))+radius/min(radii(ph))<1
        for other_position,other_radius in spheres[i+1:]:
            assert np.linalg.norm(position-other_position)>radius+other_radius
