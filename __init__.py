"""
runmonitor — a lean, local experiment tracker with a live web dashboard.
Import and go.  Dashboard auto-starts on port 8080.
"""

import json
import uuid
import threading
import time
from . import server  # noqa: F401 — starts the daemon
from . import storage


class Run:
    """A single experiment run.  Created via rm.init()."""

    def __init__(self, run_id: str, project_id: int, name: str | None,
                 config: dict, total_steps: int | None):
        self._id = run_id
        self._project_id = project_id
        self._name = name
        self._config = config
        self._total_steps = total_steps
        self._finished = False
        self._sysmon_stop = threading.Event()
        self._sysmon_thread = None
        self._start_sysmon()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str | None:
        return self._name

    def log(self, metrics: dict, step: int) -> None:
        """Log a dictionary of metric-name → float at a given step."""
        if self._finished:
            raise RuntimeError("Cannot log to a finished run.")
        if not isinstance(metrics, dict):
            raise TypeError("metrics must be a dict")
        storage.log_metrics(self._id, metrics, step)

    def save(self, filepath: str) -> dict:
        """Save an artifact file alongside this run. Returns artifact info dict."""
        return storage.save_artifact(self._id, filepath)

    def finish(self) -> None:
        """Mark the run as successfully finished."""
        if self._finished:
            return
        self._stop_sysmon()
        storage.finish_run(self._id, "finished")
        self._finished = True

    def fail(self) -> None:
        """Mark the run as crashed."""
        if self._finished:
            return
        self._stop_sysmon()
        storage.finish_run(self._id, "crashed")
        self._finished = True

    # ── system metrics background thread ───────────────────

    def _start_sysmon(self):
        """Start a daemon thread that logs CPU/RAM every 10 seconds."""
        def _collect():
            try:
                import psutil
                has_psutil = True
            except ImportError:
                has_psutil = False

            last_cpu_sample = None
            step_counter = 0
            while not self._sysmon_stop.wait(timeout=10):
                if not has_psutil:
                    return
                step_counter += 1
                try:
                    cpu = psutil.cpu_percent(interval=0.1)
                    mem = psutil.virtual_memory().percent
                    storage.log_system_metrics(self._id, step_counter, cpu, mem)
                except Exception:
                    pass

        self._sysmon_thread = threading.Thread(
            target=_collect, name="rm-sysmon", daemon=True
        )
        self._sysmon_thread.start()

    def _stop_sysmon(self):
        self._sysmon_stop.set()
        if self._sysmon_thread:
            self._sysmon_thread.join(timeout=2)


def init(project: str, name: str | None = None, config: dict | None = None,
         total_steps: int | None = None) -> Run:
    """
    Create (or reuse) a project and start a new run.

        import runmonitor as rm
        run = rm.init("mnist-experiment", config={"lr": 0.001}, total_steps=1000)

    Opens http://localhost:8080 for the live dashboard.
    """
    storage.init_db()
    project_id = storage.create_project(project)
    run_id = uuid.uuid4().hex[:12]
    config_json = json.dumps(config or {})
    storage.create_run(run_id, project_id, name, config_json, total_steps)
    return Run(run_id, project_id, name, config or {}, total_steps)
