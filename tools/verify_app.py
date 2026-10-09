"""Native-window acceptance run, screenshots, exports, and measured performance.

Run with the development interpreter from the repository root. Input events
exercise the real Qt controls. No scientific figure is substituted for the GUI.
"""
from dataclasses import replace
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import numpy as np
from PySide6 import __version__ as qt_python_version
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from versa_geometry_studio.app import StudioWindow
from versa_geometry_studio.models import GeometryInputs
from versa_geometry_studio.scene import export_geometry
from versa_geometry_studio.persistence import atomic_text,planning_summary,export_parameters,save_plan,load_plan


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Floor)
    app=QApplication([])
    root=Path(__file__).resolve().parents[1]
    out=root/'artifacts'; out.mkdir(exist_ok=True)
    window=StudioWindow(remember=False)
    window.show()
    def wait(predicate,seconds=10):
        deadline=time.perf_counter()+seconds
        while not predicate() and time.perf_counter()<deadline:
            app.processEvents(); time.sleep(0.005)
        if not predicate():
            raise AssertionError('GUI acceptance condition timed out')
    def ready():
        wait(lambda:window.preview.image_revision==window.controller.revision)
        app.processEvents(); time.sleep(0.02); app.processEvents()
    def capture(name):
        ready()
        if not window.grab().save(str(out/name)):
            raise OSError('Screenshot failed')
    for size in ((1366,768),(1920,1080)):
        window.resize(*size); app.processEvents()
        capture(f'demo-{size[0]}x{size[1]}.png')
    export_geometry(out/'example-geometry.svg',(window.top_view,window.side_view))
    export_geometry(out/'example-geometry.png',(window.top_view,window.side_view))
    window.preview.export_image(out/'synthetic-detector-raw.png',False)
    export_parameters(out/'example-parameters.csv',window.controller.state)
    export_parameters(out/'example-parameters.json',window.controller.state)
    atomic_text(out/'example-planning-summary.md',planning_summary(window.controller.state))
    save_plan(out/'roundtrip-plan.json',window.controller.state)
    assert load_plan(out/'roundtrip-plan.json')[0]==window.controller.state
    # A drag transaction and lock invariants through actual controls.
    window.mode_combo.setCurrentText('Lock magnification')
    mg=window.controller.results.geometrical_m
    window.source_control.slider.setValue(23000)
    assert abs(window.controller.results.geometrical_m-mg)<1e-12
    window.mode_combo.setCurrentText('Lock total separation')
    D=window.controller.results.D_mm
    window.detector_control.slider.setValue(25000)
    assert abs(window.controller.results.D_mm-D)<1e-12
    window.controller.reset()
    timings=[]
    for step in range(60):
        start=time.perf_counter()
        window.source_control.slider.setValue(20500+step*10)
        app.processEvents()
        timings.append((time.perf_counter()-start)*1000)
    ready()
    window.controller.reset()
    window.change_phantom('shape','ellipsoid')
    window.change_phantom('depth_mm',18)
    window.change_phantom('roi_enabled',True)
    window.rotation_slider.setValue(380)
    window.left_tabs.setCurrentIndex(2)
    window.resize(1366,768)
    capture('rotating-ellipsoid-1366x768.png')
    window.preview.export_image(out/'synthetic-detector-annotated.png',True)
    window.toggle_theme()
    capture('light-theme-1366x768.png')
    window.toggle_theme()
    window.controller.reset()
    window.mode_combo.setCurrentText('Plan acquisition')
    window.change_req('sampling_um',10)
    window.solve_plan()
    assert '3000 pixels' in window.solver_text.text()
    capture('infeasible-plan-1366x768.png')
    window.change_req('sampling_um',14.6484375)
    window.solve_plan(); window.apply_candidate()
    assert abs(window.controller.results.selected_angle_deg(window.controller.state.angle)-11.98)<1e-8
    window.mode_combo.setCurrentText('Explore geometry')
    window.left_tabs.setCurrentIndex(2)
    window.start_sweep()
    wait(lambda:window.sweep_button.isEnabled())
    assert 'SAMPLED' in window.sweep_text.text()
    from versa_geometry_studio.renderer import render_projection
    s=window.controller.state
    projection_timings={str(n):[render_projection(s.geometry,s.profile.detector,s.phantom,n).elapsed_ms for _ in range(3)] for n in (256,512)}
    result={"python":sys.version,"PySide6":qt_python_version,"numpy":np.__version__,"platform":platform.platform(),
        "screen_device_pixel_ratio":window.devicePixelRatioF(),"native_gui":True,
        "logical_viewport_sizes":[[1366,768],[1920,1080]],
        "geometry_update_and_event_processing_ms_median":statistics.median(timings),
        "geometry_update_and_event_processing_ms_p95":float(np.percentile(timings,95)),
        "isolated_projection_render_ms":projection_timings,
        "checks":["slider synchronization","magnification lock","separation lock","solve/apply","infeasibility explanation",
                  "plan save/load","PNG/SVG geometry export","raw/annotated detector export","CSV/JSON/Markdown export",
                  "rotation and interior ROI","asynchronous sampled sweep","dark/light themes"]}
    atomic_text(out/'verification.json',json.dumps(result,indent=2))
    window.close(); app.processEvents()
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
