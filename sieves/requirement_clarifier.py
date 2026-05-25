import json
from typing import Any

from llm import call_llm_json, load_text_file


REQUIREMENT_PROMPT_PATH = "sieves/prompts/requirement_system.txt"

REQUIRED_FIELDS: dict[str, type] = {
    "goal": str,
    "target_users": list,
    "functional_requirements": list,
    "constraints": list,
    "acceptance_criteria": list,
    "unresolved_items": list,
    "inconsistencies": list,
    "assumptions": list,
}


def validate_requirement_spec(spec: dict[str, Any]) -> None:
    if not isinstance(spec, dict):
        raise RuntimeError("requirement artifact must be a JSON object")

    expected_fields = set(REQUIRED_FIELDS)
    actual_fields = set(spec)

    missing_fields = expected_fields - actual_fields
    if missing_fields:
        raise RuntimeError(
            "requirement artifact missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    extra_fields = actual_fields - expected_fields
    if extra_fields:
        raise RuntimeError(
            "requirement artifact has unexpected fields: "
            + ", ".join(sorted(extra_fields))
        )

    for field, expected_type in REQUIRED_FIELDS.items():
        value = spec[field]

        if not isinstance(value, expected_type):
            raise RuntimeError(
                f"requirement artifact field '{field}' must be "
                f"{expected_type.__name__}, got {type(value).__name__}"
            )

        if isinstance(value, list):
            for index, item in enumerate(value):
                if not isinstance(item, str):
                    raise RuntimeError(
                        f"requirement artifact field '{field}' item at index "
                        f"{index} must be str, got {type(item).__name__}"
                    )


def clarify_requirement(user_intent: str) -> dict[str, Any]:
    if not user_intent.strip():
        raise ValueError("user_intent must not be empty")

    system_prompt = load_text_file(REQUIREMENT_PROMPT_PATH)

    requirement_spec = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_intent,
    )

    validate_requirement_spec(requirement_spec)
    return requirement_spec


def refine_requirement(
    current_spec: dict[str, Any],
    current_question: str,
    user_answer: str,
) -> dict[str, Any]:
    if not current_spec:
        raise ValueError("current_spec must not be empty")

    validate_requirement_spec(current_spec)

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

    requirement_spec = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(
            refinement_input,
            ensure_ascii=False,
            indent=2,
        ),
    )

    validate_requirement_spec(requirement_spec)
    return requirement_spec


def get_open_issues(requirement_spec: dict[str, Any]) -> list[str]:
    validate_requirement_spec(requirement_spec)

    issues: list[str] = []

    issues.extend(requirement_spec["unresolved_items"])
    issues.extend(requirement_spec["inconsistencies"])

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