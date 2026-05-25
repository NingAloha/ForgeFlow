import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_text_file(path: str | Path) -> str:
    file_path = Path(path)

    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    if not file_path.exists():
        raise RuntimeError(f"text file not found: {file_path}")

    return file_path.read_text(encoding="utf-8").strip()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"{name} is not set")

    return value


def create_client() -> OpenAI:
    load_dotenv(PROJECT_ROOT / ".env")

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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("model returned empty content")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"model returned invalid JSON: {content}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"model returned JSON but not an object: {content}")

    return parsed