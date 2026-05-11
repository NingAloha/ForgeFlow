from __future__ import annotations

from dataclasses import dataclass


ALLOWED_COMMANDS = {
    "/status",
    "/open spec",
    "/open solution",
    "/open design",
    "/run",
    "/help",
    "/quit",
    "/exit",
}


@dataclass(slots=True)
class ParsedCommand:
    raw: str
    command: str
    argument: str


def parse_command(raw: str) -> ParsedCommand:
    text = raw.strip()
    if not text:
        return ParsedCommand(raw=raw, command="", argument="")
    if not text.startswith("/"):
        return ParsedCommand(raw=raw, command="text", argument=text)
    if text == "/open spec":
        return ParsedCommand(raw=raw, command="/open", argument="spec")
    if text == "/open solution":
        return ParsedCommand(raw=raw, command="/open", argument="solution")
    if text == "/open design":
        return ParsedCommand(raw=raw, command="/open", argument="design")
    if text in {"/status", "/run", "/help", "/quit", "/exit"}:
        return ParsedCommand(raw=raw, command=text, argument="")
    return ParsedCommand(raw=raw, command="unknown", argument=text)
