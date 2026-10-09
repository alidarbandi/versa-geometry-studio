import os
import pytest

@pytest.fixture(scope="session")
def qapp():
    # Native windows are used on Windows. Linux CI can opt into software offscreen.
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()

