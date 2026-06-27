"""Run the dashboard standalone — no training script needed.

    runmonitor                     # if pip-installed (console script)
    python -m runmonitor           # from a checkout / vendored copy
    RUNMONITOR_PORT=9000 runmonitor # choose a port (set before launch)

Importing ``runmonitor`` already auto-starts the dashboard daemon, so this
just makes sure it's up, opens a browser, and keeps the process alive.
"""
import argparse
import os
import threading
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="runmonitor",
        description="Live, terminal-styled experiment-tracking dashboard.",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Preferred port (most reliable via RUNMONITOR_PORT before launch).",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser window.",
    )
    args = parser.parse_args()
    if args.port:
        os.environ.setdefault("RUNMONITOR_PORT", str(args.port))

    from .storage import init_db
    from . import server

    init_db()
    server._start_server()  # idempotent — reuses the daemon if already running
    url = f"http://localhost:{server._port}"
    print(f"  runmonitor dashboard → {url}")
    if args.port and args.port != server._port:
        print(f"  (port {args.port} was unavailable; bound {server._port} instead)")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        threading.Event().wait()  # block forever; Ctrl-C to quit
    except KeyboardInterrupt:
        print("\n  bye.")


if __name__ == "__main__":
    main()
