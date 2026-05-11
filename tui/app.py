from __future__ import annotations

from agents.orchestrator import Orchestrator, Stage
from agents.state_manager import StateManager

from tui.commands import parse_command
from tui.event_stream import EventStream
from tui.screens import render_screen
from tui.widgets import render_input_hint, render_status_bar


class ForgeShellApp:
    def __init__(self, state_dir: str | None = None) -> None:
        self.orchestrator = Orchestrator(
            state_manager=StateManager(state_dir=state_dir)
            if state_dir is not None
            else None
        )
        self.state_manager = self.orchestrator.state_manager
        self.events = EventStream()
        self.final_stage: Stage | str = Stage.INIT
        self.decision_type = "STAY"
        self.last_prompt = ""

    def _snapshot(self) -> str:
        return render_screen(
            status_bar=render_status_bar(self.final_stage, self.decision_type),
            events=self.events.tail(),
            input_hint=render_input_hint(),
        )

    def _run_once(self, prompt: str) -> None:
        result = self.orchestrator.orchestrate(prompt, original_request=prompt or self.last_prompt)
        self.final_stage = result.decision.final_stage
        self.decision_type = str(result.diagnostic.get("decision_type", ""))
        self.events.append("run", result.summary)
        if result.decision.wait_for_user_input:
            self.events.append("wait", "流程正在等待用户输入")

    def _open_state(self, key: str) -> None:
        mapping = {
            "spec": "spec",
            "solution": "solution",
            "design": "system_design",
        }
        target = mapping.get(key)
        if target is None:
            self.events.append("error", f"不支持的状态视图: {key}")
            return
        payload = self.state_manager.load_state(target)
        summary = ", ".join(sorted(payload.keys()))
        self.events.append("open", f"{target} 字段: {summary}")

    def _show_status(self) -> None:
        states = self.state_manager.load_all_states()
        question = states.get("question_state", {})
        self.events.append(
            "status",
            (
                f"阶段={self.final_stage}, 决策={self.decision_type}, "
                f"提问状态={question.get('status', 'idle')}"
            ),
        )

    def handle_line(self, line: str) -> bool:
        parsed = parse_command(line)
        if parsed.command in {"/quit", "/exit"}:
            self.events.append("system", "已退出")
            return False
        if parsed.command == "/help":
            self.events.append("help", render_input_hint())
            return True
        if parsed.command == "/status":
            self._show_status()
            return True
        if parsed.command == "/open":
            self._open_state(parsed.argument)
            return True
        if parsed.command == "/run":
            self._run_once(self.last_prompt)
            return True
        if parsed.command == "text":
            self.last_prompt = parsed.argument
            self.events.append("input", f"已设置输入: {parsed.argument}")
            return True
        self.events.append("error", f"不支持的命令: {line.strip()}")
        return True

    def run(self) -> int:
        print(self._snapshot())
        while True:
            try:
                line = input("forgeflow> ")
            except EOFError:
                break
            keep_running = self.handle_line(line)
            print(self._snapshot())
            if not keep_running:
                break
        return 0
