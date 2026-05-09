from __future__ import annotations

import json
from urllib.parse import parse_qs
from wsgiref.util import setup_testing_defaults

from .service import HabitService


def _json(start_response, status: str, payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _parse_body(environ) -> dict[str, object]:
    length = int(environ.get("CONTENT_LENGTH") or "0")
    if length <= 0:
        return {}
    raw = environ["wsgi.input"].read(length)
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def create_app(service: HabitService):
    def app(environ, start_response):
        setup_testing_defaults(environ)
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "")

        try:
            if method == "GET" and path == "/health":
                return _json(start_response, "200 OK", {"ok": True})

            if method == "POST" and path == "/habits":
                body = _parse_body(environ)
                habit = service.create_habit(
                    name=str(body.get("name", "")),
                    description=str(body.get("description", "")),
                    reminder_time=str(body.get("reminder_time", "")),
                )
                return _json(start_response, "201 Created", habit)

            if method == "GET" and path == "/habits":
                return _json(start_response, "200 OK", {"items": service.list_habits()})

            if path.startswith("/habits/"):
                parts = path.strip("/").split("/")
                if len(parts) >= 2:
                    habit_id = int(parts[1])

                    if len(parts) == 2 and method == "PATCH":
                        body = _parse_body(environ)
                        habit = service.update_habit(
                            habit_id,
                            name=body.get("name") if "name" in body else None,
                            description=(
                                body.get("description")
                                if "description" in body
                                else None
                            ),
                            reminder_time=(
                                body.get("reminder_time")
                                if "reminder_time" in body
                                else None
                            ),
                            active=body.get("active") if "active" in body else None,
                        )
                        return _json(start_response, "200 OK", habit)

                    if len(parts) == 2 and method == "DELETE":
                        service.delete_habit(habit_id)
                        return _json(start_response, "200 OK", {"deleted": True})

                    if len(parts) == 3 and parts[2] == "checkins" and method == "POST":
                        body = _parse_body(environ)
                        payload = service.add_checkin(
                            habit_id,
                            checkin_date=(
                                str(body.get("date")) if body.get("date") else None
                            ),
                        )
                        return _json(start_response, "200 OK", payload)

                    if len(parts) == 3 and parts[2] == "summary" and method == "GET":
                        query = parse_qs(environ.get("QUERY_STRING", ""))
                        payload = {
                            "habit": service.get_habit(habit_id),
                            "streak": service.calculate_streak(
                                habit_id,
                                end_date=(query.get("end_date") or [None])[0],
                            ),
                        }
                        return _json(start_response, "200 OK", payload)

            if method == "GET" and path == "/weekly-summary":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                payload = service.weekly_summary(
                    end_date=(query.get("end_date") or [None])[0]
                )
                return _json(start_response, "200 OK", payload)

            return _json(start_response, "404 Not Found", {"error": "Not found"})
        except (ValueError, LookupError) as exc:
            return _json(start_response, "400 Bad Request", {"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            return _json(start_response, "500 Internal Server Error", {"error": str(exc)})

    return app
