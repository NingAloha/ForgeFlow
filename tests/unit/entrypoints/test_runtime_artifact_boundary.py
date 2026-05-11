from __future__ import annotations

import unittest
from pathlib import Path


class RuntimeArtifactBoundaryTests(unittest.TestCase):
    def test_gitignore_contains_runtime_boundary_rules(self) -> None:
        gitignore_path = Path(__file__).resolve().parents[3] / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")

        required_rules = [
            ".forgeflow/state/",
            ".forgeflow/generated/",
            ".forgeflow/runs/",
            "runs/*",
            "!runs/manual_reviews/",
            "!runs/manual_reviews/**",
        ]

        for rule in required_rules:
            with self.subTest(rule=rule):
                self.assertIn(rule, content)


if __name__ == "__main__":
    unittest.main()
