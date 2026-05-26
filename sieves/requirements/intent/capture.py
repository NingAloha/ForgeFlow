import json
from pathlib import Path
from typing import Any

from llm import call_llm_json, load_text_file
from sieves.requirements.io import save_requirements
from sieves.requirements.validator import validate_requirements_artifact


PROMPT_PATH = Path(__file__).parent / "prompts" / "capture_system.txt"


def capture_intent(user_input: str) -> dict[str, Any]:
    if not user_input.strip():
        raise ValueError("user_input must not be empty")

    system_prompt = load_text_file(str(PROMPT_PATH))

    artifact = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_input,
    )

    validate_requirements_artifact(artifact)
    return artifact


def print_requirements_artifact(artifact: dict[str, Any]) -> None:
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


def main() -> None:
    user_input = input("Requirement> ").strip()

    artifact = capture_intent(user_input)

    save_requirements(artifact)

    print("\nSaved requirements artifact:")
    print_requirements_artifact(artifact)


if __name__ == "__main__":
    main()