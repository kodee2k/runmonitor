"""
Flask server that auto-starts in a daemon thread on first import.
Serves the dashboard + JSON API.
"""

import threading
import os
import time
import socket
from flask import Flask, jsonify, request, send_from_directory

from . import storage

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

_started = False
_port = 8080


def _find_port(start=8080):
    """Find the first available port starting from `start`."""
    for p in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


# ── API routes ──────────────────────────────────────────────────

@app.route("/api/projects")
def api_projects():
    return jsonify(storage.get_projects())


@app.route("/api/runs")
def api_runs():
    project = request.args.get("project")
    return jsonify(storage.get_runs(project))


@app.route("/api/runs/<run_id>/config")
def api_run_config(run_id):
    row = storage.get_run_config(run_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@app.route("/api/runs/<run_id>/metrics")
def api_run_metrics(run_id):
    key = request.args.get("key")
    limit = request.args.get("limit")
    if limit:
        limit = int(limit)
    return jsonify(storage.get_metrics(run_id, key, limit))


@app.route("/api/runs/<run_id>/metrics/live")
def api_run_metrics_live(run_id):
    """Return only metrics with step > `since` for efficient polling."""
    since = request.args.get("since", 0, type=int)
    all_metrics = storage.get_metrics(run_id)
    filtered = [m for m in all_metrics if m["step"] > since]
    return jsonify(filtered)


@app.route("/api/runs/<run_id>/artifacts")
def api_run_artifacts(run_id):
    return jsonify(storage.get_artifacts(run_id))


@app.route("/api/runs/<run_id>/system")
def api_run_system(run_id):
    return jsonify(storage.get_system_metrics(run_id))


@app.route("/api/runs/<run_id>/export")
def api_run_export(run_id):
    fmt = request.args.get("format", "json")
    metrics = storage.get_metrics(run_id)
    config = storage.get_run_config(run_id)

    if fmt == "csv":
        import csv
        import io
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["step", "key", "value", "timestamp"])
        for m in metrics:
            writer.writerow([m["step"], m["key"], m["value"], m["timestamp"]])
        csv_str = out.getvalue()
        from flask import Response
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"},
        )
    else:
        return jsonify({
            "run_id": run_id,
            "config": config,
            "metrics": metrics,
            "artifacts": storage.get_artifacts(run_id),
            "system_metrics": storage.get_system_metrics(run_id),
        })


@app.route("/api/runs/<run_id>/compare")
def api_run_compare(run_id):
    """Return metrics for two runs keyed by the same metric name."""
    other_id = request.args.get("other")
    key = request.args.get("key")
    if not other_id or not key:
        return jsonify({"error": "need `other` and `key` params"}), 400
    run_a = storage.get_metrics(run_id, key=key)
    run_b = storage.get_metrics(other_id, key=key)
    return jsonify({
        "run_a": {"id": run_id, "metrics": run_a},
        "run_b": {"id": other_id, "metrics": run_b},
    })


# ── Dashboard ───────────────────────────────────────────────────

@app.route("/")
def dashboard():
    from flask import render_template
    return render_template("dashboard.html", port=_port)


# ── Daemon start ────────────────────────────────────────────────

def _start_server():
    global _started, _port
    if _started:
        return
    _started = True
    _port = _find_port(8080)

    def _run():
        app.run(host="127.0.0.1", port=_port, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, name="runmonitor-server", daemon=True)
    t.start()
    time.sleep(0.3)  # give it a moment to bind


import os as _os
if not _os.environ.get("RUNMONITOR_STANDALONE"):
    _start_server()
