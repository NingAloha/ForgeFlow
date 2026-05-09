# Habit Tracker (Real Mini Project)

A runnable mini project built with Python standard library + SQLite.

## Features

- Habit CRUD
- Daily check-in per habit
- Consecutive streak calculation
- Weekly summary across habits
- Basic reminder field storage (`reminder_time`)

## Run

```bash
python3 examples/habit_tracker/run.py --host 127.0.0.1 --port 8081
```

Health check:

```bash
curl http://127.0.0.1:8081/health
```

## API Examples

Create habit:

```bash
curl -X POST http://127.0.0.1:8081/habits \
  -H 'Content-Type: application/json' \
  -d '{"name":"Read 20 minutes","description":"Daily reading","reminder_time":"21:00"}'
```

List habits:

```bash
curl http://127.0.0.1:8081/habits
```

Add check-in:

```bash
curl -X POST http://127.0.0.1:8081/habits/1/checkins \
  -H 'Content-Type: application/json' \
  -d '{"date":"2026-05-10"}'
```

Habit summary:

```bash
curl http://127.0.0.1:8081/habits/1/summary
```

Weekly summary:

```bash
curl http://127.0.0.1:8081/weekly-summary
```

## Tests

```bash
python3 -m unittest discover -s examples/habit_tracker/tests -p 'test_*.py' -v
```
