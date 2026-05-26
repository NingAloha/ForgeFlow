import json
from pathlib import Path
from typing import Any

from llm import call_llm_json, load_text_file
from sieves.requirements.io import load_requirements, save_requirements
from sieves.requirements.validator import (
    validate_allowed_mutation,
    validate_requirements_artifact,
)


PROMPT_PATH = Path(__file__).parent / "prompts" / "constraints_system.txt"

CONSTRAINTS_ALLOWED_PATHS: set[tuple[str, ...]] = {
    ("scope", "constraints"),
    ("open_questions",),
}


def update_constraints(
    requirements_artifact: dict[str, Any],
    current_question: str,
    user_answer: str,
) -> dict[str, Any]:
    if not isinstance(requirements_artifact, dict):
        raise ValueError("requirements_artifact must be a dict")

    validate_requirements_artifact(requirements_artifact)

    if not current_question.strip():
        raise ValueError("current_question must not be empty")

    if not user_answer.strip():
        raise ValueError("user_answer must not be empty")

    system_prompt = load_text_file(str(PROMPT_PATH))

    payload = {
        "requirements_artifact": requirements_artifact,
        "current_question": current_question,
        "user_answer": user_answer,
    }

    proposed_artifact = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
    )

    validate_requirements_artifact(proposed_artifact)

    validate_allowed_mutation(
        before=requirements_artifact,
        after=proposed_artifact,
        allowed_paths=CONSTRAINTS_ALLOWED_PATHS,
    )

    return proposed_artifact


def _find_constraints_question(artifact: dict[str, Any]) -> str:
    open_questions = artifact.get("open_questions", [])

    if not isinstance(open_questions, list):
        raise RuntimeError("requirements artifact.open_questions must be list")

    for question in open_questions:
        if not isinstance(question, str):
            raise RuntimeError("requirements artifact.open_questions must contain strings")

        if "约束" in question:
            return question

    raise RuntimeError("no constraints open question found")


def print_requirements_artifact(artifact: dict[str, Any]) -> None:
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


def main() -> None:
    artifact = load_requirements()

    current_question = _find_constraints_question(artifact)

    print(f"Current question:\n{current_question}")

    user_answer = input("\nAnswer> ").strip()

    updated_artifact = update_constraints(
        requirements_artifact=artifact,
        current_question=current_question,
        user_answer=user_answer,
    )

    save_requirements(updated_artifact)

    print("\nSaved requirements artifact:")
    print_requirements_artifact(updated_artifact)


if __name__ == "__main__":
    main()
