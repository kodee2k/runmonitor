# runmonitor

Lean, local experiment tracker with a live, **terminal-styled** web dashboard. Import and go.

```python
import runmonitor as rm

run = rm.init("my-experiment", config={"lr": 0.001, "batch_size": 32}, total_steps=1000)

for step in range(1000):
    loss, acc = train_step()
    run.log({"loss": loss, "accuracy": acc}, step)
    if step % 100 == 0:
        run.save("checkpoint.pt")

run.finish()
```

Open `http://localhost:8080` — your loss curve is already live and drawing itself.

## Install

```bash
pip install runmonitor                 # core
pip install "runmonitor[system]"       # + CPU/RAM tracking (psutil)
```

Then in any training script:

```python
import runmonitor as rm
```

Or run the dashboard on its own (no training script needed):

```bash
runmonitor                 # opens the dashboard in your browser
python -m runmonitor       # equivalent, for a checkout/vendored copy
RUNMONITOR_PORT=9000 runmonitor   # pick a port (set before launch)
```

## The dashboard

A single, evolving view in the empero black/purple palette:

| Element | What it shows |
|---|---|
| **Metric ticker** | Every logged metric as `key=value`. Click one to **select** it. |
| **Live hero curve** | The selected metric, drawn point-by-point and growing every step. |
| **Anomaly detection** | Rolling z-score flags spikes — vertical markers on the curve + a status line ("⚠ anomaly at step N" / "● all calm"). |
| **Run header** | Run id, current step, status pill, elapsed, steps/sec, ETA, progress bar. |
| **Streak / best badges** | 🔥 improving-streak and 🏆 personal-best on the selected metric (direction-aware). |
| **Compare** | Pick a second run to overlay on the selected metric. |
| **System pane** | CPU % and RAM % over time (needs `psutil`). |
| **Hyperparameters / Artifacts** | Config passed to `rm.init()` and any saved files. |
| **Export** | Download the full run as CSV or JSON. |
| **Theme** | Midnight (black/purple) by default; toggle to light bone-paper. |

## API

```python
# Start a run (creates the project if new)
run = rm.init(project: str, name: str | None = None,
              config: dict | None = None,
              total_steps: int | None = None) -> Run

run.log(metrics: dict[str, float], step: int)   # log metrics at a step
run.save(filepath: str) -> dict                  # save an artifact file
run.finish()                                     # mark finished
run.fail()                                       # mark crashed
```

## Storage

Everything lives in `~/.runmonitor/`:
- `runs.db` — SQLite database (WAL mode, thread-safe)
- `artifacts/<run_id>/` — saved files per run

No database setup, no API keys, no cloud.

## Requirements

- Python 3.10+
- Flask
- Chart.js (loaded from CDN in the dashboard)
- `psutil` (optional, for system metrics)

## Publishing to PyPI (maintainers)

```bash
python -m pip install --upgrade build twine
python -m build                 # → dist/runmonitor-<version>.tar.gz + .whl
python -m twine check dist/*
python -m twine upload dist/*   # needs a PyPI account + API token
```

Bump `version` in `pyproject.toml` before each release.
