"""Central immutable state, undo transactions, and revision-tagged worker results."""
from dataclasses import replace
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, Slot
from .models import AppState, GeometryInputs
from .physics import calculate
from .projection import validate_placement, sweep_coverage
from .renderer import render_projection


class WorkerSignals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class Worker(QRunnable):
    def __init__(self, revision, fn):
        super().__init__()
        self.revision, self.fn = revision, fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.done.emit(self.revision, self.fn())
        except Exception as exc:
            self.signals.failed.emit(self.revision, str(exc))


class Controller(QObject):
    changed = Signal(object, object, int)
    preview_ready = Signal(object)
    validation_failed = Signal(str)
    history_changed = Signal(bool, bool)
    sweep_ready = Signal(object)

    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = state or AppState()
        self.state.validate()
        validate_placement(self.state.geometry, self.state.phantom)
        self.results = calculate(self.state.geometry, self.state.profile.detector)
        self.revision = 0
        self.undo_stack, self.redo_stack = [], []
        self._transaction = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self._busy = False
        self._pending = None
        self._worker = None
        self._sweep_worker = None
        self.refine = QTimer(self)
        self.refine.setSingleShot(True)
        self.refine.setInterval(240)
        self.refine.timeout.connect(lambda: self.request_preview(512))

    def begin_transaction(self):
        if self._transaction is None:
            self._transaction = self.state

    def end_transaction(self):
        if self._transaction is not None and self._transaction != self.state:
            self.undo_stack.append(self._transaction)
            self.undo_stack = self.undo_stack[-100:]
            self.redo_stack.clear()
        self._transaction = None
        self.history_changed.emit(bool(self.undo_stack), bool(self.redo_stack))

    def set_state(self, state, record=True):
        try:
            state.validate()
            validate_placement(state.geometry, state.phantom)
            results = calculate(state.geometry, state.profile.detector)
        except (ValueError, TypeError, OverflowError) as exc:
            self.validation_failed.emit(str(exc))
            return False
        if state == self.state:
            return True
        if record and self._transaction is None:
            self.undo_stack.append(self.state)
            self.undo_stack = self.undo_stack[-100:]
            self.redo_stack.clear()
        self.state, self.results = state, results
        self.revision += 1
        self.changed.emit(state, results, self.revision)
        self.history_changed.emit(bool(self.undo_stack), bool(self.redo_stack))
        self.request_preview(256)
        self.refine.start()
        return True

    def move_distance(self, which, value):
        g, mode = self.state.geometry, self.state.mode
        try:
            if which not in ("a", "b"):
                raise ValueError("Unknown distance control")
            a, b = (float(value), g.b_mm) if which == "a" else (g.a_mm, float(value))
            if mode == "Lock magnification":
                ratio = g.b_mm/g.a_mm
                if which == "a":
                    b = ratio*a
                else:
                    a = b/ratio
            elif mode == "Lock total separation":
                if which == "a":
                    b = g.a_mm+g.b_mm-a
                else:
                    a = g.a_mm+g.b_mm-b
            return self.set_state(replace(self.state, geometry=GeometryInputs(a, b)))
        except (ValueError, ZeroDivisionError) as exc:
            self.validation_failed.emit(str(exc))
            return False

    def undo(self):
        self.end_transaction()
        if self.undo_stack:
            self.redo_stack.append(self.state)
            self.set_state(self.undo_stack.pop(), record=False)

    def redo(self):
        self.end_transaction()
        if self.redo_stack:
            self.undo_stack.append(self.state)
            self.set_state(self.redo_stack.pop(), record=False)

    def reset(self):
        self.set_state(AppState())

    def request_preview(self, resolution=256):
        self._pending = (self.revision, self.state, resolution)
        if not self._busy:
            self._start_pending()

    def _start_pending(self):
        if self._pending is None:
            return
        rev, state, resolution = self._pending
        self._pending, self._busy = None, True
        worker = Worker(rev, lambda: render_projection(state.geometry, state.profile.detector, state.phantom, resolution, rev))
        self._worker = worker
        worker.signals.done.connect(self._preview_done)
        worker.signals.failed.connect(self._preview_failed)
        self.pool.start(worker)

    @Slot(int, object)
    def _preview_done(self, revision, result):
        if revision == self.revision:
            self.preview_ready.emit(result)
        self._busy = False
        self._start_pending()

    @Slot(int, str)
    def _preview_failed(self, revision, message):
        if revision == self.revision:
            self.validation_failed.emit(message)
        self._busy = False
        self._start_pending()

    def request_sweep(self, increment_deg=5):
        state, rev = self.state, self.revision
        if self._sweep_worker is not None:
            return False
        worker = Worker(rev, lambda: sweep_coverage(state.geometry, state.profile.detector, state.phantom, increment_deg))
        self._sweep_worker = worker
        worker.signals.done.connect(self._sweep_done)
        worker.signals.failed.connect(self._sweep_failed)
        self.pool.start(worker)
        return True

    @Slot(int, object)
    def _sweep_done(self, revision, result):
        self._sweep_worker = None
        if revision == self.revision:
            self.sweep_ready.emit(result)
        else:
            self.sweep_ready.emit({"stale": True})

    @Slot(int, str)
    def _sweep_failed(self, revision, message):
        self._sweep_worker = None
        self.sweep_ready.emit({"error": message})

    def shutdown(self):
        self.refine.stop()
        self._pending = None
        self.pool.waitForDone()
