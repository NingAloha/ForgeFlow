import json
from pathlib import Path
from typing import Any

from sieves.requirements.validator import validate_requirements_artifact


DEFAULT_REQUIREMENTS_PATH = Path("requirements.json")

EXAMPLE_REQUIREMENTS_PATH = Path(__file__).parent / "requirements.example.json"


def requirements_exists(
    path: Path = DEFAULT_REQUIREMENTS_PATH,
) -> bool:
    return path.exists()


def load_requirements(
    path: Path = DEFAULT_REQUIREMENTS_PATH,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"requirements file not found: {path}")

    raw = path.read_text(encoding="utf-8").strip()

    if not raw:
        raise RuntimeError(f"requirements file is empty: {path}")

    try:
        artifact = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"requirements file contains invalid JSON: {path}") from exc

    if not isinstance(artifact, dict):
        raise RuntimeError(f"requirements file must contain a JSON object: {path}")

    if validate:
        validate_requirements_artifact(artifact)

    return artifact


def save_requirements(
    artifact: dict[str, Any],
    path: Path = DEFAULT_REQUIREMENTS_PATH,
    *,
    validate: bool = True,
) -> None:
    if validate:
        validate_requirements_artifact(artifact)

    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_requirements_example(
    path: Path = EXAMPLE_REQUIREMENTS_PATH,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    return load_requirements(path, validate=validate)


def initialize_requirements_from_example(
    output_path: Path = DEFAULT_REQUIREMENTS_PATH,
    example_path: Path = EXAMPLE_REQUIREMENTS_PATH,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"requirements file already exists: {output_path}")

    artifact = load_requirements_example(example_path, validate=True)

    save_requirements(
        artifact,
        output_path,
        validate=True,
    )

    return artifact