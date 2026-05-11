from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import sqlite3


def _today() -> date:
    return date.today()


def _iso_day(value: str | None) -> str:
    if not value:
        return _today().isoformat()
    return date.fromisoformat(value).isoformat()


@dataclass(slots=True)
class HabitService:
    conn: sqlite3.Connection

    def create_habit(
        self,
        name: str,
        description: str = "",
        reminder_time: str = "",
    ) -> dict[str, object]:
        name = name.strip()
        if not name:
            raise ValueError("Habit name is required.")
        now = datetime.utcnow().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            """
            INSERT INTO habits(name, description, reminder_time, created_at, active)
            VALUES(?, ?, ?, ?, 1)
            """,
            (name, description.strip(), reminder_time.strip(), now),
        )
        self.conn.commit()
        return self.get_habit(int(cursor.lastrowid))

    def list_habits(self, include_inactive: bool = False) -> list[dict[str, object]]:
        sql = "SELECT * FROM habits"
        params: tuple[object, ...] = ()
        if not include_inactive:
            sql += " WHERE active = 1"
        sql += " ORDER BY id ASC"
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_habit(row) for row in rows]

    def get_habit(self, habit_id: int) -> dict[str, object]:
        row = self.conn.execute(
            "SELECT * FROM habits WHERE id = ?", (habit_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Habit not found.")
        return self._row_to_habit(row)

    def update_habit(
        self,
        habit_id: int,
        name: str | None = None,
        description: str | None = None,
        reminder_time: str | None = None,
        active: bool | None = None,
    ) -> dict[str, object]:
        current = self.get_habit(habit_id)
        next_name = current["name"] if name is None else name.strip()
        if not next_name:
            raise ValueError("Habit name is required.")
        next_description = (
            current["description"] if description is None else description.strip()
        )
        next_reminder = (
            current["reminder_time"] if reminder_time is None else reminder_time.strip()
        )
        next_active = current["active"] if active is None else bool(active)
        self.conn.execute(
            """
            UPDATE habits
            SET name = ?, description = ?, reminder_time = ?, active = ?
            WHERE id = ?
            """,
            (next_name, next_description, next_reminder, int(next_active), habit_id),
        )
        self.conn.commit()
        return self.get_habit(habit_id)

    def delete_habit(self, habit_id: int) -> None:
        self.get_habit(habit_id)
        self.conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        self.conn.commit()

    def add_checkin(
        self, habit_id: int, checkin_date: str | None = None
    ) -> dict[str, object]:
        self.get_habit(habit_id)
        day = _iso_day(checkin_date)
        now = datetime.utcnow().isoformat(timespec="seconds")
        self.conn.execute(
            """
            INSERT OR IGNORE INTO checkins(habit_id, checkin_date, created_at)
            VALUES(?, ?, ?)
            """,
            (habit_id, day, now),
        )
        self.conn.commit()
        return {
            "habit_id": habit_id,
            "checkin_date": day,
            "streak": self.calculate_streak(habit_id, end_date=day),
        }

    def calculate_streak(self, habit_id: int, end_date: str | None = None) -> int:
        self.get_habit(habit_id)
        end = date.fromisoformat(_iso_day(end_date))
        rows = self.conn.execute(
            "SELECT checkin_date FROM checkins WHERE habit_id = ?",
            (habit_id,),
        ).fetchall()
        days = {date.fromisoformat(row["checkin_date"]) for row in rows}

        streak = 0
        cursor = end
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def weekly_summary(self, end_date: str | None = None) -> dict[str, object]:
        end = date.fromisoformat(_iso_day(end_date))
        start = end - timedelta(days=6)

        habits = self.list_habits()
        report: list[dict[str, object]] = []
        for habit in habits:
            habit_id = int(habit["id"])
            count = self.conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM checkins
                WHERE habit_id = ? AND checkin_date BETWEEN ? AND ?
                """,
                (habit_id, start.isoformat(), end.isoformat()),
            ).fetchone()["cnt"]
            report.append(
                {
                    "habit_id": habit_id,
                    "name": habit["name"],
                    "weekly_checkins": int(count),
                    "streak": self.calculate_streak(habit_id, end_date=end.isoformat()),
                }
            )
        return {
            "range_start": start.isoformat(),
            "range_end": end.isoformat(),
            "habits": report,
        }

    def _row_to_habit(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "reminder_time": str(row["reminder_time"]),
            "created_at": str(row["created_at"]),
            "active": bool(row["active"]),
        }
