import json
from typing import Any

from llm import call_llm_json, load_text_file


REQUIREMENT_PROMPT_PATH = "sieves/prompts/requirement_system.txt"


def clarify_requirement(user_intent: str) -> dict[str, Any]:
    if not user_intent.strip():
        raise ValueError("user_intent must not be empty")

    system_prompt = load_text_file(REQUIREMENT_PROMPT_PATH)

    return call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_intent,
    )


def refine_requirement(
    current_spec: dict[str, Any],
    current_question: str,
    user_answer: str,
) -> dict[str, Any]:
    if not current_spec:
        raise ValueError("current_spec must not be empty")

    if not current_question.strip():
        raise ValueError("current_question must not be empty")

    if not user_answer.strip():
        raise ValueError("user_answer must not be empty")

    system_prompt = load_text_file(REQUIREMENT_PROMPT_PATH)

    refinement_input = {
        "current_requirement_artifact": current_spec,
        "current_question": current_question,
        "user_answer": user_answer,
        "instruction": (
            "Update the current requirement artifact using the user's answer "
            "to the current question. "
            "If the answer resolves the question, remove it from unresolved_items. "
            "Preserve stable requirements unless explicitly changed by the user. "
            "Do not regenerate the artifact from scratch."
        ),
    }

    return call_llm_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(
            refinement_input,
            ensure_ascii=False,
            indent=2,
        ),
    )


def get_open_issues(requirement_spec: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    unresolved_items = requirement_spec.get("unresolved_items", [])
    inconsistencies = requirement_spec.get("inconsistencies", [])

    if isinstance(unresolved_items, list):
        issues.extend(str(item) for item in unresolved_items)

    if isinstance(inconsistencies, list):
        issues.extend(str(item) for item in inconsistencies)

    return issues


def has_open_issues(requirement_spec: dict[str, Any]) -> bool:
    return bool(get_open_issues(requirement_spec))


def get_next_issue(requirement_spec: dict[str, Any]) -> str | None:
    issues = get_open_issues(requirement_spec)

    if not issues:
        return None

    return issues[0]


def print_requirement_spec(requirement_spec: dict[str, Any]) -> None:
    print(json.dumps(requirement_spec, ensure_ascii=False, indent=2))


def interactive_clarification_loop() -> dict[str, Any]:
    user_intent = input("Requirement> ").strip()

    if not user_intent:
        raise ValueError("requirement must not be empty")

    current_spec = clarify_requirement(user_intent)

    while has_open_issues(current_spec):
        print("\nCurrent requirement artifact:")
        print_requirement_spec(current_spec)

        current_question = get_next_issue(current_spec)

        if current_question is None:
            break

        print(f"\nCurrent question:\n{current_question}")

        user_answer = input("\nAnswer> ").strip()

        if not user_answer:
            raise ValueError("answer must not be empty")

        current_spec = refine_requirement(
            current_spec=current_spec,
            current_question=current_question,
            user_answer=user_answer,
        )

    return current_spec


if __name__ == "__main__":
    final_spec = interactive_clarification_loop()

    print("\nFinal requirement artifact:")
    print_requirement_spec(final_spec)