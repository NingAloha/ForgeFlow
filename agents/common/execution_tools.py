from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


@dataclass(slots=True)
class ExecutionTrace:
    workspace_path: str = ""
    file_writes: list[str] = field(default_factory=list)
    command_results: list[CommandResult] = field(default_factory=list)


class WorkspaceExecutor:
    COMMAND_ALLOWLIST: tuple[tuple[str, ...], ...] = (
        (
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ),
        (
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ),
    )

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.trace = ExecutionTrace(workspace_path=str(self.workspace_root))

    def _resolve_path(self, relative_path: str) -> Path:
        candidate = (self.workspace_root / relative_path).resolve()
        if (
            self.workspace_root not in candidate.parents
            and candidate != self.workspace_root
        ):
            raise ValueError("Path escapes workspace root.")
        return candidate

    def write_file(self, relative_path: str, content: str) -> str:
        path = self._resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        rel = str(path.relative_to(self.workspace_root))
        self.trace.file_writes.append(rel)
        return rel

    def run_command(
        self, command: list[str], cwd: str | Path | None = None, timeout: int = 30
    ) -> CommandResult:
        if not command:
            raise ValueError("Command cannot be empty.")
        if not self._is_allowed(command):
            raise PermissionError(f"Command not allowed: {' '.join(command)}")

        run_cwd = self.workspace_root if cwd is None else Path(cwd).resolve()
        if (
            self.workspace_root not in run_cwd.parents
            and run_cwd != self.workspace_root
        ):
            raise ValueError("Command cwd escapes workspace root.")

        completed = subprocess.run(
            command,
            cwd=run_cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = CommandResult(
            command=list(command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        self.trace.command_results.append(result)
        return result

    def _is_allowed(self, command: list[str]) -> bool:
        for prefix in self.COMMAND_ALLOWLIST:
            if tuple(command[: len(prefix)]) == prefix:
                return True
        return False
