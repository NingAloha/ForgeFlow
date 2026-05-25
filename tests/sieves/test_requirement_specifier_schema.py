import copy
import sys
import types
import unittest

# Stub llm module so importing requirement_specifier does not require dotenv/openai.
llm_stub = types.ModuleType("llm")
llm_stub.call_llm_json = lambda *args, **kwargs: {}
llm_stub.load_text_file = lambda *args, **kwargs: ""
sys.modules.setdefault("llm", llm_stub)

from sieves.requirement_specifier import validate_requirement_package


def make_valid_package() -> dict:
    return {
        "product_overview": {
            "purpose": "构建一个桌面IDE",
            "scope": ["覆盖代码编辑与调试能力"],
            "non_goals": [],
            "target_users": ["学生", "开发者"],
        },
        "system_context": {
            "application_type": "桌面应用",
            "target_platforms": ["macOS"],
            "operational_environment": ["离线运行"],
            "external_dependencies": [],
        },
        "functional_requirements": [
            {
                "id": "FR-001",
                "description": "支持代码编辑",
                "priority": "must",
                "source": "输入需求",
                "acceptance_criteria": ["用户可打开并保存本地代码文件"],
            }
        ],
        "non_functional_requirements": [
            {
                "id": "NFR-001",
                "category": "usability",
                "description": "界面简洁",
                "priority": "should",
                "acceptance_criteria": ["主要功能可在两次点击内到达"],
            }
        ],
        "interface_requirements": [
            {
                "id": "IR-001",
                "interface_type": "user_interface",
                "description": "提供桌面图形界面",
            }
        ],
        "data_requirements": [
            {
                "id": "DR-001",
                "description": "支持本地工程文件读写",
            }
        ],
        "constraints": ["桌面应用"],
        "assumptions": [],
        "unresolved_items": ["目标平台是否仅限macOS"],
        "inconsistencies": [],
    }


class TestRequirementSpecifierSchema(unittest.TestCase):
    def test_valid_package_passes(self) -> None:
        package = make_valid_package()

        validate_requirement_package(package)

    def test_missing_top_level_field_raises(self) -> None:
        package = make_valid_package()
        del package["constraints"]

        with self.assertRaisesRegex(RuntimeError, "constraints"):
            validate_requirement_package(package)

    def test_extra_top_level_field_raises(self) -> None:
        package = make_valid_package()
        package["extra"] = []

        with self.assertRaisesRegex(RuntimeError, "extra"):
            validate_requirement_package(package)

    def test_product_overview_missing_field_raises(self) -> None:
        package = make_valid_package()
        del package["product_overview"]["scope"]

        with self.assertRaisesRegex(RuntimeError, "scope"):
            validate_requirement_package(package)

    def test_system_context_wrong_type_raises(self) -> None:
        package = make_valid_package()
        package["system_context"]["target_platforms"] = "macOS"

        with self.assertRaisesRegex(RuntimeError, "target_platforms"):
            validate_requirement_package(package)

    def test_functional_requirement_missing_field_raises(self) -> None:
        package = make_valid_package()
        item = copy.deepcopy(package["functional_requirements"][0])
        del item["source"]
        package["functional_requirements"] = [item]

        with self.assertRaisesRegex(RuntimeError, "source"):
            validate_requirement_package(package)

    def test_priority_invalid_raises(self) -> None:
        package = make_valid_package()
        package["functional_requirements"][0]["priority"] = "high"

        with self.assertRaisesRegex(RuntimeError, "priority"):
            validate_requirement_package(package)

    def test_nfr_category_invalid_raises(self) -> None:
        package = make_valid_package()
        package["non_functional_requirements"][0]["category"] = "latency"

        with self.assertRaisesRegex(RuntimeError, "category"):
            validate_requirement_package(package)

    def test_interface_type_invalid_raises(self) -> None:
        package = make_valid_package()
        package["interface_requirements"][0]["interface_type"] = "socket"

        with self.assertRaisesRegex(RuntimeError, "interface_type"):
            validate_requirement_package(package)

    def test_string_list_with_non_string_item_raises(self) -> None:
        package = make_valid_package()
        package["constraints"] = ["桌面应用", 123]

        with self.assertRaisesRegex(RuntimeError, "constraints"):
            validate_requirement_package(package)


if __name__ == "__main__":
    unittest.main()
