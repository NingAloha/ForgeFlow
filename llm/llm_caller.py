import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(relative_path: str) -> str:
    prompt_path = PROMPTS_DIR / relative_path

    if not prompt_path.exists():
        raise RuntimeError(f"prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"{name} is not set")

    return value


def create_client() -> OpenAI:
    load_dotenv()

    return OpenAI(
        api_key=get_required_env("MODEL_API_KEY"),
        base_url=get_required_env("MODEL_BASE_URL"),
        timeout=30.0,
    )


def call_llm_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    if not system_prompt.strip():
        raise ValueError("system_prompt must not be empty")

    if not user_prompt.strip():
        raise ValueError("user_prompt must not be empty")

    client = create_client()
    model = get_required_env("MODEL_NAME")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("model returned empty content")

    try:
        parsed = json.loads(content)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"model returned invalid JSON: {content}"
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"model returned JSON but not an object: {content}"
        )

    return parsed


if __name__ == "__main__":
    system_prompt = load_prompt("json_only_system.txt")
    user_prompt = input("Prompt> ")

    result = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))