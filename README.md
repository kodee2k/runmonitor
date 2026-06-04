# runmonitor

Lean, local experiment tracker with a live web dashboard. Import and go.

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

Open `http://localhost:8080` — your loss curve is already live.

## Features

- **Live dashboard** — charts update every 2s while your script runs
- **Arbitrary metrics** — log any dict of floats, any number of keys, charts appear automatically
- **Artifact saving** — `run.save("model.pt")` copies files alongside the run
- **Run comparison** — overlay two runs on the same charts from the dashboard
- **Gamification** — streaks (🔥) and personal-best badges (🏆) keep training fun
- **System metrics** — auto-tracks CPU and RAM if `psutil` is installed
- **Export** — download full run data as CSV or JSON
- **Dark theme** — out of the box
- **Zero config** — no servers to start, no API keys, no cloud

## Install

```bash
pip install -e .            # or copy the folder into your project
pip install psutil          # optional, for CPU/RAM tracking
```

If installed as a package:

```python
import runmonitor as rm
```

If vendored (copy the folder into your project):

```python
from runmonitor import Run, init
```

## Dashboard

| Element | What it shows |
|---|---|
| Summary cards | Status, current step, elapsed time, steps/sec |
| Progress bar | Step / total steps with percentage (if `total_steps` set) |
| Config table | All config keys passed to `rm.init()` |
| Charts grid | One chart per metric key, auto-created as new keys appear |
| Compare dropdown | Pick a second run to overlay on charts |
| Streak counter | Consecutive improving steps on your primary metric |
| System pane | CPU % and RAM % charts over time |
| Artifacts table | Saved files with path and size |
| Export button | Download CSV or JSON |

## API

```python
# Start a run (creates project if new)
run = rm.init(project: str, name: str | None = None,
              config: dict | None = None,
              total_steps: int | None = None) -> Run

# Log metrics at a step
run.log(metrics: dict[str, float], step: int)

# Save an artifact file
run.save(filepath: str) -> dict

# Mark run as finished or crashed
run.finish()
run.fail()
```

## Storage

Everything lives in `~/.runmonitor/`:
- `runs.db` — SQLite database (WAL mode, thread-safe)
- `artifacts/<run_id>/` — saved files per run

## Requirements

- Python 3.10+
- Flask
- Chart.js (loaded from CDN in the dashboard)

No database setup. No external services.
