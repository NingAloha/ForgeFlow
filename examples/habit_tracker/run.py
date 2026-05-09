from __future__ import annotations

import argparse
from pathlib import Path
from wsgiref.simple_server import make_server

from habit_tracker.api import create_app
from habit_tracker.db import connect, init_db
from habit_tracker.service import HabitService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run habit tracker API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent / "data" / "habit_tracker.db"),
        help="SQLite database path",
    )
    args = parser.parse_args()

    conn = connect(args.db)
    init_db(conn)
    service = HabitService(conn)
    app = create_app(service)

    with make_server(args.host, args.port, app) as server:
        print(f"Habit tracker running on http://{args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
