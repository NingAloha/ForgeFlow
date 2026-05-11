from __future__ import annotations

from tui.event_stream import Event


def render_screen(status_bar: str, events: list[Event], input_hint: str) -> str:
    lines = [status_bar, "", "Event Stream:"]
    if not events:
        lines.append("- (no events yet)")
    else:
        for item in events:
            lines.append(f"- [{item.timestamp}] {item.kind}: {item.message}")
    lines.extend(["", input_hint])
    return "\n".join(lines)
