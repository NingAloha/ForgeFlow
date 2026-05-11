from __future__ import annotations

from ..common.text import TextHelper


class ImplementationPlanningMixin(TextHelper):
    RESERVED_GENERIC_MODULES = {"core", "utils", "app"}

    def get_design_modules(self, design: dict[str, object]) -> list[str]:
        modules: list[str] = []
        for item in design.get("project_structure", {}).get("modules", []):
            raw_name = str(item)
            normalized = self.normalize_text(raw_name)
            if not normalized:
                continue
            module_name = self.slugify_text(raw_name)
            if not module_name:
                continue
            if module_name in self.RESERVED_GENERIC_MODULES:
                continue
            modules.append(module_name)
        return modules

    def select_primary_module_name(
        self,
        current_state: dict[str, object],
        design_modules: list[str],
    ) -> str:
        persisted = self.slugify_text(str(current_state.get("module_name", "")))
        if persisted and persisted in design_modules:
            return persisted
        if design_modules:
            return design_modules[0]
        return ""

    def _normalize_text_entries(self, value: object) -> list[str]:
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = [value]
        else:
            return []
        return [self.normalize_text(str(item)) for item in items if self.normalize_text(str(item))]

    def match_module_contract(self, module_name: str, design: dict[str, object]) -> dict[str, object] | None:
        contracts = design.get("contracts", [])
        fallback_contract: dict[str, object] | None = None
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            if fallback_contract is None:
                fallback_contract = contract
            contract_name = self.normalize_text(str(contract.get("name", ""))).lower()
            if module_name and module_name in self.slugify_text(contract_name):
                return contract
            input_blob = " ".join(self._normalize_text_entries(contract.get("input", []))).lower()
            output_blob = " ".join(self._normalize_text_entries(contract.get("output", []))).lower()
            module_blob = module_name.replace("_", " ").lower()
            if module_blob and (module_blob in input_blob or module_blob in output_blob):
                return contract
        if len(contracts) == 1:
            return fallback_contract
        return None

    def has_module_data_flow(self, module_name: str, design: dict[str, object]) -> bool:
        data_flow = design.get("data_flow", [])
        for item in design.get("data_flow", []):
            if not isinstance(item, dict):
                continue
            joined = " ".join(
                [
                    self.normalize_text(str(item.get("contract_name", ""))),
                    self.normalize_text(str(item.get("trigger", ""))),
                    self.normalize_text(str(item.get("notes", ""))),
                    self.normalize_text(str(item.get("from", ""))),
                    " ".join(self._normalize_text_entries(item.get("to", []))),
                ]
            ).lower()
            if module_name.replace("_", " ").lower() in joined or module_name in joined:
                return True
        module_count = len(self.get_design_modules(design))
        if len(data_flow) == 1 and module_count <= 2:
            return True
        return False

    def find_module_directory(self, module_name: str, design: dict[str, object]) -> str:
        directories = design.get("project_structure", {}).get("directories", [])
        module_token = f"/{module_name}/"
        for item in directories:
            directory = self.normalize_text(str(item))
            if not directory:
                continue
            wrapped = f"/{directory.strip('/')}/"
            if module_token in wrapped:
                return directory
        return f"src/{module_name}/"

    def build_module_steps(self, module_name: str, contract: dict[str, object] | None) -> list[str]:
        step_items = [
            f"Prepare module handoff scope for {module_name} using design project structure",
            "Map contract inputs to implementation intake checklist",
            "Map contract outputs to implementation status checkpoints",
        ]
        if contract and contract.get("failure_handling"):
            step_items.append(
                "Map failure_handling categories into implementation execution checkpoints"
            )
        else:
            step_items.append("Record unresolved failure-handling alignment as blocker context")
        return step_items

    def build_module_done_criteria(self) -> list[str]:
        return [
            "Module handoff plan references design contract input and output semantics",
            "Failure categories are represented in execution checklist",
            "Suggested tests include happy path and at least one failure path",
            "Implementation status can mark contract_compliance=true for handoff alignment",
        ]

    def build_module_suggested_tests(self, module_name: str) -> list[str]:
        module_phrase = module_name.replace("_", " ")
        return [
            f"Validate {module_phrase} happy path behavior against contract outputs",
            f"Validate {module_phrase} failure path coverage for input_errors or processing_errors",
        ]

    def build_expected_artifact_types(self) -> list[str]:
        return [
            "implementation checklist notes",
            "status mapping entries",
            "test suggestion entries",
        ]

    def build_module_note(
        self,
        module_name: str,
        steps: list[str],
        done_criteria: list[str],
    ) -> str:
        steps_text = " | ".join(steps)
        done_text = " | ".join(done_criteria)
        return f"module={module_name}; steps=[{steps_text}]; done=[{done_text}]"
