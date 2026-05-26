from typing import Any


REQUIREMENTS_FIELDS: dict[str, type] = {
    "artifact_type": str,
    "schema_version": str,
    "maturity": str,
    "intent": dict,
    "product": dict,
    "scope": dict,
    "functional_requirements": list,
    "non_functional_requirements": list,
    "external_interfaces": list,
    "data_requirements": list,
    "open_questions": list,
    "inconsistencies": list,
}


INTENT_FIELDS: dict[str, type] = {
    "raw_input": str,
    "goal": str,
    "domain": str,
}


PRODUCT_FIELDS: dict[str, type] = {
    "target_users": list,
    "application_type": list,
    "target_platforms": list,
}


SCOPE_FIELDS: dict[str, type] = {
    "capability_categories": list,
    "constraints": list,
    "non_goals": list,
}


ALLOWED_ARTIFACT_TYPES = {"requirements"}

ALLOWED_SCHEMA_VERSIONS = {"0.1"}

ALLOWED_MATURITY = {
    "intent",
    "scope",
    "capability",
    "requirement",
    "review_ready",
}


def _validate_exact_fields(
    value: dict[str, Any],
    expected_fields: dict[str, type],
    object_name: str,
) -> None:
    if not isinstance(value, dict):
        raise RuntimeError(f"{object_name} must be a JSON object")

    expected = set(expected_fields)
    actual = set(value)

    missing = expected - actual
    if missing:
        raise RuntimeError(
            f"{object_name} missing required fields: "
            + ", ".join(sorted(missing))
        )

    extra = actual - expected
    if extra:
        raise RuntimeError(
            f"{object_name} has unexpected fields: "
            + ", ".join(sorted(extra))
        )

    for field, expected_type in expected_fields.items():
        field_value = value[field]

        if not isinstance(field_value, expected_type):
            raise RuntimeError(
                f"{object_name}.{field} must be {expected_type.__name__}, "
                f"got {type(field_value).__name__}"
            )


def _validate_string_list(value: Any, field_path: str) -> None:
    if not isinstance(value, list):
        raise RuntimeError(f"{field_path} must be list")

    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise RuntimeError(
                f"{field_path}[{index}] must be str, "
                f"got {type(item).__name__}"
            )


def _validate_object_list(value: Any, field_path: str) -> None:
    if not isinstance(value, list):
        raise RuntimeError(f"{field_path} must be list")

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"{field_path}[{index}] must be object, "
                f"got {type(item).__name__}"
            )


def validate_requirements_artifact(artifact: dict[str, Any]) -> None:
    _validate_exact_fields(
        artifact,
        REQUIREMENTS_FIELDS,
        "requirements artifact",
    )

    artifact_type = artifact["artifact_type"]
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        raise RuntimeError(
            "requirements artifact.artifact_type must be one of "
            f"{sorted(ALLOWED_ARTIFACT_TYPES)}, got {artifact_type!r}"
        )

    schema_version = artifact["schema_version"]
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        raise RuntimeError(
            "requirements artifact.schema_version must be one of "
            f"{sorted(ALLOWED_SCHEMA_VERSIONS)}, got {schema_version!r}"
        )

    maturity = artifact["maturity"]
    if maturity not in ALLOWED_MATURITY:
        raise RuntimeError(
            "requirements artifact.maturity must be one of "
            f"{sorted(ALLOWED_MATURITY)}, got {maturity!r}"
        )

    _validate_exact_fields(
        artifact["intent"],
        INTENT_FIELDS,
        "requirements artifact.intent",
    )

    _validate_exact_fields(
        artifact["product"],
        PRODUCT_FIELDS,
        "requirements artifact.product",
    )

    _validate_exact_fields(
        artifact["scope"],
        SCOPE_FIELDS,
        "requirements artifact.scope",
    )

    _validate_string_list(
        artifact["product"]["target_users"],
        "requirements artifact.product.target_users",
    )
    _validate_string_list(
        artifact["product"]["application_type"],
        "requirements artifact.product.application_type",
    )
    _validate_string_list(
        artifact["product"]["target_platforms"],
        "requirements artifact.product.target_platforms",
    )

    _validate_string_list(
        artifact["scope"]["capability_categories"],
        "requirements artifact.scope.capability_categories",
    )
    _validate_string_list(
        artifact["scope"]["constraints"],
        "requirements artifact.scope.constraints",
    )
    _validate_string_list(
        artifact["scope"]["non_goals"],
        "requirements artifact.scope.non_goals",
    )

    _validate_object_list(
        artifact["functional_requirements"],
        "requirements artifact.functional_requirements",
    )
    _validate_object_list(
        artifact["non_functional_requirements"],
        "requirements artifact.non_functional_requirements",
    )
    _validate_object_list(
        artifact["external_interfaces"],
        "requirements artifact.external_interfaces",
    )
    _validate_object_list(
        artifact["data_requirements"],
        "requirements artifact.data_requirements",
    )

    _validate_string_list(
        artifact["open_questions"],
        "requirements artifact.open_questions",
    )
    _validate_string_list(
        artifact["inconsistencies"],
        "requirements artifact.inconsistencies",
    )