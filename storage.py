import sqlite3
import os
import shutil
import threading

DB_DIR = os.path.expanduser("~/.runmonitor")
DB_PATH = os.path.join(DB_DIR, "runs.db")
ARTIFACTS_DIR = os.path.join(DB_DIR, "artifacts")

_lock = threading.Lock()


def get_db() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = get_db()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS runs (
            id           TEXT     PRIMARY KEY,
            project_id   INTEGER  NOT NULL REFERENCES projects(id),
            name         TEXT,
            status       TEXT     DEFAULT 'running',
            config_json  TEXT     DEFAULT '{}',
            total_steps  INTEGER,
            started_at   TEXT     DEFAULT (datetime('now')),
            finished_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT    NOT NULL REFERENCES runs(id),
            step        INTEGER NOT NULL,
            key         TEXT    NOT NULL,
            value       REAL    NOT NULL,
            timestamp   TEXT    DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_run_step ON metrics(run_id, step);
        CREATE INDEX IF NOT EXISTS idx_metrics_run_key  ON metrics(run_id, key);

        CREATE TABLE IF NOT EXISTS artifacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT    NOT NULL REFERENCES runs(id),
            filename    TEXT    NOT NULL,
            filepath    TEXT    NOT NULL,
            size_bytes  INTEGER,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS system_metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT    NOT NULL REFERENCES runs(id),
            step        INTEGER NOT NULL,
            cpu_percent REAL,
            mem_percent REAL,
            timestamp   TEXT    DEFAULT (datetime('now'))
        );
        """)
        conn.commit()
        conn.close()


def create_project(name: str) -> int:
    with _lock:
        conn = get_db()
        cur = conn.execute(
            "INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,)
        )
        if cur.rowcount == 1:
            project_id = cur.lastrowid
        else:
            row = conn.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()
            project_id = row["id"]
        conn.commit()
        conn.close()
        return project_id


def create_run(run_id: str, project_id: int, name: str | None, config_json: str, total_steps: int | None) -> dict:
    with _lock:
        conn = get_db()
        conn.execute(
            """INSERT INTO runs (id, project_id, name, config_json, total_steps)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, project_id, name, config_json, total_steps),
        )
        conn.commit()
        conn.close()


def log_metrics(run_id: str, metrics: dict, step: int):
    with _lock:
        conn = get_db()
        rows = [(run_id, step, k, v) for k, v in metrics.items()]
        conn.executemany(
            "INSERT INTO metrics (run_id, step, key, value) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        conn.close()


def finish_run(run_id: str, status: str = "finished"):
    with _lock:
        conn = get_db()
        conn.execute(
            "UPDATE runs SET status=?, finished_at=datetime('now') WHERE id=?",
            (status, run_id),
        )
        conn.commit()
        conn.close()


def get_projects() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, name, created_at FROM projects ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_runs(project_name: str | None = None) -> list[dict]:
    conn = get_db()
    if project_name:
        rows = conn.execute(
            """SELECT r.*, p.name as project_name
               FROM runs r JOIN projects p ON r.project_id = p.id
               WHERE p.name = ? ORDER BY r.started_at DESC""",
            (project_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT r.*, p.name as project_name
               FROM runs r JOIN projects p ON r.project_id = p.id
               ORDER BY r.started_at DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_metrics(run_id: str, key: str | None = None, limit: int | None = None,
                since: int | None = None) -> list[dict]:
    conn = get_db()
    clauses = ["run_id=?"]
    params: list = [run_id]
    if key:
        clauses.append("key=?")
        params.append(key)
    if since is not None:
        clauses.append("step > ?")
        params.append(since)
    order = "ORDER BY step" if key else "ORDER BY step, key"
    query = f"SELECT step, key, value, timestamp FROM metrics WHERE {' AND '.join(clauses)} {order}"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run_config(run_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT config_json, total_steps, status, started_at FROM runs WHERE id=?",
        (run_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Artifacts ──────────────────────────────────────────────

def save_artifact(run_id: str, src_path: str) -> dict:
    """Copy a file into the run's artifact directory and record it."""
    filename = os.path.basename(src_path)
    dest_dir = os.path.join(ARTIFACTS_DIR, run_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    shutil.copy2(src_path, dest_path)
    size_bytes = os.path.getsize(dest_path)

    with _lock:
        conn = get_db()
        conn.execute(
            "INSERT INTO artifacts (run_id, filename, filepath, size_bytes) VALUES (?, ?, ?, ?)",
            (run_id, filename, dest_path, size_bytes),
        )
        conn.commit()
        conn.close()
    return {"filename": filename, "filepath": dest_path, "size_bytes": size_bytes}


def get_artifacts(run_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT filename, filepath, size_bytes, created_at FROM artifacts WHERE run_id=? ORDER BY created_at",
        (run_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── System metrics ─────────────────────────────────────────

def log_system_metrics(run_id: str, step: int, cpu: float, mem: float):
    with _lock:
        conn = get_db()
        conn.execute(
            "INSERT INTO system_metrics (run_id, step, cpu_percent, mem_percent) VALUES (?, ?, ?, ?)",
            (run_id, step, cpu, mem),
        )
        conn.commit()
        conn.close()


def get_system_metrics(run_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT step, cpu_percent, mem_percent, timestamp FROM system_metrics WHERE run_id=? ORDER BY step",
        (run_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
