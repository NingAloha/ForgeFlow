from __future__ import annotations

from pathlib import Path
import unittest


class LLMBoundaryResidualGuardTests(unittest.TestCase):
    def test_stage_agents_do_not_use_raw_llm_boundary(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        stage_agent_paths = [
            repo_root / "agents" / "requirements_engineer" / "agent.py",
            repo_root / "agents" / "solution_engineer" / "agent.py",
            repo_root / "agents" / "system_designer" / "agent.py",
            repo_root / "agents" / "implementation_engineer" / "agent.py",
            repo_root / "agents" / "test_validation_engineer" / "agent.py",
        ]
        forbidden_tokens = [
            "LLMAdapter",
            "generate_json",
            "generate_text",
            "json.loads",
            "llm_success",
            "fallback_used",
        ]
        for path in stage_agent_paths:
            content = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                self.assertNotIn(token, content, f"{path} contains forbidden token: {token}")


if __name__ == "__main__":
    unittest.main()
