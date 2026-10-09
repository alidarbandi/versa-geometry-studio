"""python -m versa_geometry_studio [plan.json] [--smoke-test PATH]."""
import argparse
from pathlib import Path
import sys
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from .app import StudioWindow
from .persistence import load_plan, load_profile
from .models import AppState
from dataclasses import replace


def main():
    parser = argparse.ArgumentParser(description="Versa Geometry Studio desktop planner")
    parser.add_argument("plan", nargs="?", help="Versioned JSON acquisition plan")
    parser.add_argument("--smoke-test", metavar="SCREENSHOT", help="Launch, capture a real window and exit (packaging verification)")
    args = parser.parse_args()
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Versa Geometry Studio")
    app.setOrganizationName("GeometryStudio")
    state = None
    if args.plan:
        try:
            state, warnings = load_plan(args.plan)
            for warning in warnings:
                print(warning, file=sys.stderr)
        except (OSError, ValueError, TypeError) as exc:
            print(f"Cannot open plan: {exc}", file=sys.stderr)
            return 2
    window = StudioWindow(state, remember=not bool(args.smoke_test))
    if state is None and window.settings:
        profile_path = window.settings.value("last_profile", "")
        if profile_path:
            try:
                window.controller.set_state(replace(AppState(), profile=load_profile(profile_path)))
            except (OSError, ValueError, TypeError):
                window.statusBar().showMessage("Last profile unavailable; restored demo", 6000)
    window.show()
    if args.smoke_test:
        # Timer checks a current projection before recording the running GUI.
        attempts = [0]
        def capture():
            attempts[0] += 1
            if window.preview.image_revision != window.controller.revision and attempts[0] < 100:
                QTimer.singleShot(100, capture); return
            Path(args.smoke_test).parent.mkdir(parents=True, exist_ok=True)
            ok = window.grab().save(args.smoke_test)
            window.close()
            app.exit(0 if ok and attempts[0] < 100 else 3)
        QTimer.singleShot(700, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
