from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Event:
    timestamp: str
    kind: str
    message: str


class EventStream:
    def __init__(self, max_items: int = 200) -> None:
        self.max_items = max(1, max_items)
        self._items: list[Event] = []

    def append(self, kind: str, message: str) -> None:
        self._items.append(
            Event(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                kind=kind,
                message=message,
            )
        )
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]

    def tail(self, limit: int = 12) -> list[Event]:
        return self._items[-max(1, limit) :]
