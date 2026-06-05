"""Run the dashboard standalone — no training script needed.
Usage: python -m runmonitor [--port PORT]
"""
import os
import sys

os.environ["RUNMONITOR_STANDALONE"] = "1"

if __name__ == "__main__":
    port = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[1] == "--port" else 8080
    from .storage import init_db
    from .server import app, _find_port
    p = _find_port(port)
    init_db()
    print(f"Dashboard → http://localhost:{p}")
    app.run(host="127.0.0.1", port=p, debug=False, use_reloader=False)
