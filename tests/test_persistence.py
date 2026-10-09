from dataclasses import replace
import json
import pytest
from versa_geometry_studio.models import AppState
from versa_geometry_studio.physics import calculate
from versa_geometry_studio.persistence import (save_plan,load_plan,save_profile,load_profile,plan_document,
    parameter_csv,planning_summary)


def test_plan_roundtrip_full_precision(tmp_path):
    s=AppState(); s=replace(s,geometry=replace(s.geometry,a_mm=205.123456789123),requirements=replace(s.requirements,sampling_mode='no coarser'))
    path=tmp_path/'plan.json'; save_plan(path,s)
    loaded,warnings=load_plan(path)
    assert loaded==s and not warnings
    assert calculate(loaded.geometry,loaded.profile.detector)==calculate(s.geometry,s.profile.detector)
    save_profile(tmp_path/'profile.json',s.profile)
    assert load_profile(tmp_path/'profile.json')==s.profile


def test_recomputes_tampered_results(tmp_path):
    document=plan_document(AppState()); document['computed_results']['sampling_um']=123
    path=tmp_path/'plan.json'; path.write_text(json.dumps(document),encoding='utf-8')
    loaded,warnings=load_plan(path)
    assert warnings and calculate(loaded.geometry,loaded.profile.detector).sampling_um!=123


@pytest.mark.parametrize('change', ['units','version','nan'])
def test_malformed_plans_rejected(tmp_path,change):
    raw=plan_document(AppState())
    if change=='units': raw['units']['geometry']='cm'
    if change=='version': raw['schema_version']=999
    if change=='nan': raw['state']['geometry']['a_mm']=float('nan')
    path=tmp_path/'bad.json'; path.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError): load_plan(path)


def test_export_has_units_equations_and_provenance():
    s=AppState()
    assert 'µm/pixel' in parameter_csv(s)
    summary=planning_summary(s)
    assert 'M_g = (a+b)/a' in summary
    assert '135 mm' in summary and 'stage' in summary and 'v11.x' in summary
