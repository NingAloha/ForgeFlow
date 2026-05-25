import json
import sys
from typing import Any

from llm import call_llm_json, load_text_file


SPECIFIER_PROMPT_PATH = "sieves/prompts/requirement_specifier_system.txt"

TOP_LEVEL_FIELDS: dict[str, type] = {
    "product_overview": dict,
    "system_context": dict,
    "functional_requirements": list,
    "non_functional_requirements": list,
    "interface_requirements": list,
    "data_requirements": list,
    "constraints": list,
    "assumptions": list,
    "unresolved_items": list,
    "inconsistencies": list,
}

PRODUCT_OVERVIEW_FIELDS: dict[str, type] = {
    "purpose": str,
    "scope": list,
    "non_goals": list,
    "target_users": list,
}

SYSTEM_CONTEXT_FIELDS: dict[str, type] = {
    "application_type": str,
    "target_platforms": list,
    "operational_environment": list,
    "external_dependencies": list,
}

FUNCTIONAL_ITEM_FIELDS: dict[str, type] = {
    "id": str,
    "description": str,
    "priority": str,
    "source": str,
    "acceptance_criteria": list,
}

NON_FUNCTIONAL_ITEM_FIELDS: dict[str, type] = {
    "id": str,
    "category": str,
    "description": str,
    "priority": str,
    "acceptance_criteria": list,
}

INTERFACE_ITEM_FIELDS: dict[str, type] = {
    "id": str,
    "interface_type": str,
    "description": str,
}

DATA_ITEM_FIELDS: dict[str, type] = {
    "id": str,
    "description": str,
}

PRIORITY_VALUES = {"must", "should", "could"}
NFR_CATEGORY_VALUES = {
    "performance",
    "reliability",
    "usability",
    "security",
    "maintainability",
    "portability",
    "compatibility",
    "other",
}
INTERFACE_TYPE_VALUES = {
    "user_interface",
    "external_system",
    "file",
    "network",
    "cli",
    "api",
    "other",
}


def _validate_exact_fields(
    value: dict[str, Any],
    required_fields: dict[str, type],
    object_name: str,
) -> None:
    expected_fields = set(required_fields)
    actual_fields = set(value)

    missing_fields = expected_fields - actual_fields
    if missing_fields:
        raise RuntimeError(
            f"{object_name} missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    extra_fields = actual_fields - expected_fields
    if extra_fields:
        raise RuntimeError(
            f"{object_name} has unexpected fields: "
            + ", ".join(sorted(extra_fields))
        )


def _validate_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise RuntimeError(
            f"field '{field_name}' must be list, got {type(value).__name__}"
        )

    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise RuntimeError(
                f"field '{field_name}' item at index {index} must be str, "
                f"got {type(item).__name__}"
            )


def _validate_typed_object(
    value: Any,
    required_fields: dict[str, type],
    object_name: str,
) -> None:
    if not isinstance(value, dict):
        raise RuntimeError(f"{object_name} must be object, got {type(value).__name__}")

    _validate_exact_fields(value, required_fields, object_name)

    for field, expected_type in required_fields.items():
        field_value = value[field]
        if not isinstance(field_value, expected_type):
            raise RuntimeError(
                f"{object_name} field '{field}' must be "
                f"{expected_type.__name__}, got {type(field_value).__name__}"
            )


def _validate_requirement_list_item(
    item: Any,
    required_fields: dict[str, type],
    list_name: str,
    index: int,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise RuntimeError(
            f"{list_name} item at index {index} must be object, "
            f"got {type(item).__name__}"
        )

    _validate_exact_fields(item, required_fields, f"{list_name} item at index {index}")

    for field, expected_type in required_fields.items():
        field_value = item[field]
        if not isinstance(field_value, expected_type):
            raise RuntimeError(
                f"{list_name} item at index {index} field '{field}' must be "
                f"{expected_type.__name__}, got {type(field_value).__name__}"
            )

    return item


def validate_requirement_package(package: dict[str, Any]) -> None:
    if not isinstance(package, dict):
        raise RuntimeError("requirement package must be a JSON object")

    _validate_exact_fields(package, TOP_LEVEL_FIELDS, "requirement package")

    for field, expected_type in TOP_LEVEL_FIELDS.items():
        value = package[field]
        if not isinstance(value, expected_type):
            raise RuntimeError(
                f"requirement package field '{field}' must be "
                f"{expected_type.__name__}, got {type(value).__name__}"
            )

    _validate_typed_object(
        package["product_overview"],
        PRODUCT_OVERVIEW_FIELDS,
        "product_overview",
    )
    _validate_string_list(package["product_overview"]["scope"], "product_overview.scope")
    _validate_string_list(
        package["product_overview"]["non_goals"],
        "product_overview.non_goals",
    )
    _validate_string_list(
        package["product_overview"]["target_users"],
        "product_overview.target_users",
    )

    _validate_typed_object(
        package["system_context"],
        SYSTEM_CONTEXT_FIELDS,
        "system_context",
    )
    _validate_string_list(
        package["system_context"]["target_platforms"],
        "system_context.target_platforms",
    )
    _validate_string_list(
        package["system_context"]["operational_environment"],
        "system_context.operational_environment",
    )
    _validate_string_list(
        package["system_context"]["external_dependencies"],
        "system_context.external_dependencies",
    )

    for index, item in enumerate(package["functional_requirements"]):
        parsed_item = _validate_requirement_list_item(
            item,
            FUNCTIONAL_ITEM_FIELDS,
            "functional_requirements",
            index,
        )
        if parsed_item["priority"] not in PRIORITY_VALUES:
            raise RuntimeError(
                f"functional_requirements item at index {index} field 'priority' "
                f"must be one of {sorted(PRIORITY_VALUES)}, "
                f"got {parsed_item['priority']!r}"
            )
        _validate_string_list(
            parsed_item["acceptance_criteria"],
            f"functional_requirements[{index}].acceptance_criteria",
        )

    for index, item in enumerate(package["non_functional_requirements"]):
        parsed_item = _validate_requirement_list_item(
            item,
            NON_FUNCTIONAL_ITEM_FIELDS,
            "non_functional_requirements",
            index,
        )
        if parsed_item["priority"] not in PRIORITY_VALUES:
            raise RuntimeError(
                f"non_functional_requirements item at index {index} field 'priority' "
                f"must be one of {sorted(PRIORITY_VALUES)}, "
                f"got {parsed_item['priority']!r}"
            )
        if parsed_item["category"] not in NFR_CATEGORY_VALUES:
            raise RuntimeError(
                f"non_functional_requirements item at index {index} field 'category' "
                f"must be one of {sorted(NFR_CATEGORY_VALUES)}, "
                f"got {parsed_item['category']!r}"
            )
        _validate_string_list(
            parsed_item["acceptance_criteria"],
            f"non_functional_requirements[{index}].acceptance_criteria",
        )

    for index, item in enumerate(package["interface_requirements"]):
        parsed_item = _validate_requirement_list_item(
            item,
            INTERFACE_ITEM_FIELDS,
            "interface_requirements",
            index,
        )
        if parsed_item["interface_type"] not in INTERFACE_TYPE_VALUES:
            raise RuntimeError(
                f"interface_requirements item at index {index} field 'interface_type' "
                f"must be one of {sorted(INTERFACE_TYPE_VALUES)}, "
                f"got {parsed_item['interface_type']!r}"
            )

    for index, item in enumerate(package["data_requirements"]):
        _validate_requirement_list_item(
            item,
            DATA_ITEM_FIELDS,
            "data_requirements",
            index,
        )

    _validate_string_list(package["constraints"], "constraints")
    _validate_string_list(package["assumptions"], "assumptions")
    _validate_string_list(package["unresolved_items"], "unresolved_items")
    _validate_string_list(package["inconsistencies"], "inconsistencies")


def specify_requirement(coarse_requirement: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(coarse_requirement, dict):
        raise ValueError("coarse_requirement must be dict")

    system_prompt = load_text_file(SPECIFIER_PROMPT_PATH)

    requirement_package = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(coarse_requirement, ensure_ascii=False, indent=2),
    )

    validate_requirement_package(requirement_package)
    return requirement_package


if __name__ == "__main__":
    raw_input = sys.stdin.read()
    coarse_requirement = json.loads(raw_input)
    requirement_package = specify_requirement(coarse_requirement)
    print(json.dumps(requirement_package, ensure_ascii=False, indent=2))
