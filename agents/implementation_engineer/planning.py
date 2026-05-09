from __future__ import annotations

from ..common.text import TextHelper


class ImplementationPlanningMixin(TextHelper):
    def select_module_name(
        self,
        current_state: dict[str, object],
        design: dict[str, object],
        solution: dict[str, object],
    ) -> str:
        persisted = self.slugify_text(str(current_state.get("module_name", "")))
        if persisted:
            return persisted

        design_modules = [
            self.slugify_text(str(module))
            for module in design.get("project_structure", {}).get("modules", [])
            if self.normalize_text(str(module))
        ]
        design_modules = [module for module in design_modules if module]
        if design_modules:
            return design_modules[0]

        module_mapping = solution.get("module_mapping", [])
        for module in module_mapping:
            module_name = self.slugify_text(str(module.get("module", "")))
            if module_name:
                return module_name
        return ""

    def build_files_touched(self, module_name: str) -> list[str]:
        if not module_name:
            return []
        return [
            f"agents/{module_name}/agent.py",
            f"tests/unit/agents/test_{module_name}.py",
            f"docs/state/contracts/{module_name}.md",
        ]

    def build_tests_touched(self, module_name: str) -> list[str]:
        if not module_name:
            return []
        return [
            f"tests/unit/integration/test_{module_name}_workflow.py",
        ]

    def evaluate_contract_compliance(
        self,
        module_name: str,
        design: dict[str, object],
    ) -> bool:
        contracts = design.get("contracts", [])
        if not contracts or not design.get("data_flow"):
            return False
        for contract in contracts:
            name = str(contract.get("name", ""))
            if module_name and module_name in name:
                return True
            output_text = str(contract.get("output", "")).lower()
            if "implementation_status" in output_text:
                return True
        return True
