"""Reproducibly create baseline profiles and demonstration plans."""
from dataclasses import replace
from pathlib import Path
from versa_geometry_studio.models import AppState,GeometryInputs
from versa_geometry_studio.persistence import save_plan,save_profile


def main():
    root=Path(__file__).resolve().parents[1]
    state=AppState()
    save_profile(root/'profiles'/'zeiss-versa-nominal.json',state.profile)
    save_plan(root/'examples'/'01-demo-30mm.json',state)
    vertical=replace(state,geometry=GeometryInputs(150,195.6),angle=replace(state.angle,axis='vertical'))
    save_plan(root/'examples'/'02-vertical-vs-diagonal.json',vertical)
    binned=replace(state,profile=state.profile.with_detector(replace(state.profile.detector,binning=2)),
                   requirements=replace(state.requirements,sampling_um=29.296875))
    save_plan(root/'examples'/'03-binning2-same-field.json',binned)
    crop=replace(state,profile=state.profile.with_detector(replace(state.profile.detector,crop_nx=1024,crop_ny=1024)),
                 requirements=replace(state.requirements,fov_x_mm=15,fov_y_mm=15),angle=replace(state.angle,envelope='crop'),
                 phantom=replace(state.phantom,roi_enabled=True))
    save_plan(root/'examples'/'04-interior-roi-crop.json',crop)
    impossible=replace(state,requirements=replace(state.requirements,sampling_um=10),mode='Plan acquisition')
    save_plan(root/'examples'/'05-infeasible-3000-pixels.json',impossible)
    rotating=replace(state,phantom=replace(state.phantom,shape='ellipsoid',depth_mm=18,rotation_deg=38,roi_enabled=True))
    save_plan(root/'examples'/'06-rotating-ellipsoid.json',rotating)


if __name__=='__main__':
    main()
