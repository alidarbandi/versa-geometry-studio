from dataclasses import replace
import time
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtGui import QMouseEvent
from versa_geometry_studio.app import StudioWindow
from versa_geometry_studio.models import AppState, GeometryInputs
from versa_geometry_studio.profile_editor import ProfileEditor
from versa_geometry_studio.scene import export_geometry
from versa_geometry_studio.renderer import RenderResult
import numpy as np


def wait_for(qapp, predicate, timeout=5):
    deadline=time.perf_counter()+timeout
    while not predicate() and time.perf_counter()<deadline:
        qapp.processEvents(); time.sleep(0.005)
    assert predicate(), 'GUI condition timed out'


@pytest.fixture
def window(qapp):
    w=StudioWindow(remember=False); w.resize(1366,768); w.show(); QTest.qWait(60)
    yield w
    w.close(); qapp.processEvents()


def test_slider_updates_scene_preview_results_and_history(window,qapp):
    c=window.controller
    old=c.revision
    slider=window.source_control.slider
    QTest.mousePress(slider,Qt.MouseButton.LeftButton,pos=QPoint(slider.width()//2,slider.height()//2))
    QTest.mouseMove(slider,QPoint(slider.width()*3//5,slider.height()//2),delay=20)
    QTest.mouseRelease(slider,Qt.MouseButton.LeftButton,pos=QPoint(slider.width()*3//5,slider.height()//2))
    assert c.revision>old
    assert window.top_view.item.results==c.results==window.side_view.item.results
    assert window.preview.revision==c.revision
    assert window.source_control.value==c.state.geometry.a_mm
    wait_for(qapp,lambda:window.preview.image_revision==c.revision)
    assert c.undo_stack
    # An obsolete worker result cannot replace the current detector image.
    image=window.preview.image.cacheKey()
    window.preview.set_render(RenderResult(c.revision-1,np.ones((16,16),dtype=np.float32),0))
    assert window.preview.image.cacheKey()==image


def test_lock_modes_undo_redo_and_exclusivity(window,qapp):
    c=window.controller
    window.mode_combo.setCurrentText('Lock magnification')
    mg=c.results.geometrical_m
    c.move_distance('a',250)
    assert c.results.geometrical_m==pytest.approx(mg,rel=1e-12)
    window.mode_combo.setCurrentText('Lock total separation')
    D=c.results.D_mm
    c.move_distance('b',300)
    assert c.results.D_mm==pytest.approx(D,rel=1e-12)
    assert c.state.mode=='Lock total separation'
    before=c.state
    c.undo(); assert c.state!=before
    c.redo(); assert c.state==before
    window.mode_combo.setCurrentText('Plan acquisition')
    assert not window.source_control.isEnabled()
    assert not window.detector_control.isEnabled()


def test_solve_apply_angle_convention_and_no_hidden_solver(window,qapp):
    c=window.controller
    geometry=c.state.geometry
    window.change_req('sampling_um',10)
    assert c.state.geometry==geometry
    window.solve_plan()
    assert '3000 pixels' in window.solver_text.text()
    assert not window.apply_button.isEnabled()
    window.change_req('sampling_um',14.6484375)
    window.mode_combo.setCurrentText('Plan acquisition')
    window.solve_plan(); assert window.apply_button.isEnabled()
    window.apply_candidate()
    assert c.results.selected_angle_deg(c.state.angle)==pytest.approx(11.98)
    window.angle_convention.setCurrentText('half')
    window.solve_plan()
    assert window.candidate.a_mm<110


def test_invalid_partial_edit_retains_scene(window,qapp):
    c=window.controller
    before=c.state
    edit=window.source_control.edit
    edit.setFocus(); edit.selectAll(); QTest.keyClicks(edit,'nan'); QTest.keyClick(edit,Qt.Key.Key_Return)
    assert c.state==before
    edit.selectAll(); QTest.keyClicks(edit,'-1'); QTest.keyClick(edit,Qt.Key.Key_Return)
    assert c.state==before
    assert window.error_label.text()
    edit.selectAll(); QTest.keyClicks(edit,'225.123456789'); QTest.keyClick(edit,Qt.Key.Key_Return)
    assert c.state.geometry.a_mm==225.123456789


def test_objective_loads_its_own_calibration_and_profile_editor(window,qapp):
    window.change_detector('pitch_um',14)
    window.objective_combo.setCurrentText('4×')
    assert window.controller.state.profile.detector.pitch_um==13.5
    assert window.controller.state.profile.detector.optical_m==4
    window.objective_combo.setCurrentText('0.4×')
    assert window.controller.state.profile.detector.pitch_um==14
    editor=ProfileEditor(window.controller.state.profile,window)
    editor.validate_accept()
    assert editor.result_profile==window.controller.state.profile


def test_projection_hover_and_scene_drag(window,qapp):
    c=window.controller
    preview=window.preview
    point=preview.image_rect().center()
    QApplication = __import__('PySide6.QtWidgets',fromlist=['QApplication']).QApplication
    event=QMouseEvent(QMouseEvent.Type.MouseMove,point,preview.mapToGlobal(point.toPoint()),
                     Qt.MouseButton.NoButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(preview,event)
    wait_for(qapp,lambda:window.top_view.item.hover_yz is not None)
    assert 'Host path' in window.inspector_label.text()
    view=window.top_view
    x=-c.state.geometry.a_mm-20
    from PySide6.QtCore import QPointF
    point=view.mapFromScene(QPointF(x,0))
    QTest.mousePress(view.viewport(),Qt.MouseButton.LeftButton,pos=point)
    destination=point+QPoint(-15,0)
    event=QMouseEvent(QMouseEvent.Type.MouseMove,destination,view.viewport().mapToGlobal(destination),
                     Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view.viewport(),event)
    QTest.mouseRelease(view.viewport(),Qt.MouseButton.LeftButton,pos=point+QPoint(-15,0))
    assert c.state.geometry.a_mm>205


def test_exports_and_layouts(window,qapp,tmp_path):
    for width,height in ((1366,768),(1920,1080)):
        window.resize(width,height); QTest.qWait(30)
        assert window.top_view.width()>400
        assert window.preview.width()>180
        assert window.detector_control.edit.isVisible()
        # Scroll content may be taller, but must fit the panel horizontally.
        area=window.left_tabs.widget(0)
        assert area.widget().width()<=area.viewport().width()+1
    wait_for(qapp,lambda:window.preview.image_revision==window.controller.revision)
    export_geometry(tmp_path/'geometry.svg',(window.top_view,window.side_view))
    export_geometry(tmp_path/'geometry.png',(window.top_view,window.side_view))
    window.preview.export_image(tmp_path/'preview.png',False)
    assert (tmp_path/'geometry.svg').read_text(encoding='utf-8').startswith('<?xml')
    assert (tmp_path/'geometry.png').stat().st_size>1000


def test_sweep_is_async_and_reports_sampled_result(window,qapp):
    window.start_sweep()
    wait_for(qapp,lambda:window.sweep_button.isEnabled())
    assert 'SAMPLED assessment' in window.sweep_text.text()
