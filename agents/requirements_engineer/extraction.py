from __future__ import annotations

import re

from ..common.text import TextHelper


class RequirementsExtractionMixin(TextHelper):
    def extract_goal_from_input(self, user_input: str) -> str:
        text = self.normalize_text(user_input)
        if not text:
            return ""
        text = re.sub(
            r"^(please\s+)?(help me\s+)?(build|create|make|design|develop)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(i want to|we need to|need to|want to)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = self.normalize_text(text)
        if not text:
            return ""
        return self.sentence_case(text)

    def extract_requirements_from_input(self, user_input: str) -> list[str]:
        text = user_input.strip()
        if not text:
            return []

        bullet_candidates: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^([-*]|\d+\.)\s+", stripped):
                bullet_candidates.append(
                    re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
                )
        if bullet_candidates:
            return self.dedupe_items(bullet_candidates)

        normalized = re.sub(r"\s+", " ", text)
        clauses = re.split(r"[。\n.;；]|(?:\s+and\s+)|(?:\s+then\s+)", normalized)
        candidates: list[str] = []
        for clause in clauses:
            cleaned = self.normalize_text(clause)
            if len(cleaned.split()) < 2:
                continue
            cleaned = re.sub(
                r"^(please\s+)?(help me\s+)?(build|create|make|design|develop)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                r"^(i want to|we need to|need to|want to)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            if len(cleaned.split()) < 2:
                continue
            candidates.append(cleaned)
        return self.dedupe_items(candidates)

    def derive_acceptance_criteria(
        self, project_goal: str, functional_requirements: list[str]
    ) -> list[str]:
        criteria: list[str] = []
        for requirement in functional_requirements[:3]:
            criteria.append(
                f"The system can {requirement[0].lower() + requirement[1:]}."
            )
        if not criteria and project_goal:
            criteria.append(
                "The delivered workflow satisfies the core goal: "
                f"{project_goal[0].lower() + project_goal[1:]}."
            )
        return self.dedupe_items(criteria)
