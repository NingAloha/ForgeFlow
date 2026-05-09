from __future__ import annotations

import sqlite3
import unittest

from examples.habit_tracker.habit_tracker.db import init_db
from examples.habit_tracker.habit_tracker.service import HabitService


class HabitServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        init_db(self.conn)
        self.service = HabitService(self.conn)

    def test_create_and_list_habit(self) -> None:
        created = self.service.create_habit("Read", "Read books", "21:00")
        self.assertEqual(created["name"], "Read")
        items = self.service.list_habits()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["reminder_time"], "21:00")

    def test_checkins_and_streak(self) -> None:
        habit = self.service.create_habit("Workout")
        habit_id = int(habit["id"])

        self.service.add_checkin(habit_id, "2026-05-08")
        self.service.add_checkin(habit_id, "2026-05-09")
        self.service.add_checkin(habit_id, "2026-05-10")

        streak = self.service.calculate_streak(habit_id, "2026-05-10")
        self.assertEqual(streak, 3)

    def test_weekly_summary(self) -> None:
        habit = self.service.create_habit("Meditation")
        habit_id = int(habit["id"])
        self.service.add_checkin(habit_id, "2026-05-07")
        self.service.add_checkin(habit_id, "2026-05-10")

        summary = self.service.weekly_summary("2026-05-10")
        self.assertEqual(summary["range_start"], "2026-05-04")
        self.assertEqual(summary["range_end"], "2026-05-10")
        self.assertEqual(summary["habits"][0]["weekly_checkins"], 2)


if __name__ == "__main__":
    unittest.main()
