from __future__ import annotations

import re


class SolutionTextHelper:
    def normalize_text(self, value: str) -> str:
        text = re.sub(r"\s+", " ", value).strip()
        return text.strip(" \t\r\n-*:;,.")

    def sentence_case(self, value: str) -> str:
        text = self.normalize_text(value)
        if not text:
            return ""
        return text[0].upper() + text[1:]

    def dedupe_items(self, items: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = self.normalize_text(item)
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(self.sentence_case(normalized))
        return deduped

    def slugify_requirement(self, requirement: str) -> str:
        text = self.normalize_text(requirement).lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")
