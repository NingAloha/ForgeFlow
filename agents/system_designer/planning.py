from __future__ import annotations

from ..common.text import TextHelper


class SystemDesignPlanningMixin(TextHelper):
    def build_project_structure(
        self, module_mapping: list[dict[str, object]]
    ) -> dict[str, list[str]]:
        modules = sorted(
            {
                self.slugify_text(str(module.get("module", "")))
                for module in module_mapping
                if self.normalize_text(str(module.get("module", "")))
            }
        )
        module_names = [module for module in modules if module]
        directories = ["agents/", "docs/", "state/", "tests/"]
        directories.extend(f"agents/{module}/" for module in module_names)
        deduped_directories: list[str] = []
        seen: set[str] = set()
        for directory in directories:
            key = directory.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped_directories.append(directory)
        return {
            "directories": deduped_directories,
            "modules": module_names,
        }

    def build_contracts(
        self, module_mapping: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        contracts: list[dict[str, object]] = []
        for module in module_mapping:
            module_name = self.slugify_text(str(module.get("module", "")))
            if not module_name:
                continue
            requirement_refs = [
                self.sentence_case(str(item))
                for item in module.get("covers_requirements", [])
                if self.normalize_text(str(item))
            ]
            contract_name = f"solution_to_{module_name}_implementation"
            contracts.append(
                {
                    "name": contract_name,
                    "contract_type": "state_handoff",
                    "producer": "Solution Engineer",
                    "consumers": ["System Designer", "Implementation Engineer"],
                    "input": [
                        {
                            "name": "solution.module_mapping",
                            "description": "Module ownership and responsibilities",
                            "required": True,
                        }
                    ],
                    "output": [
                        {
                            "name": f"implementation_status.{module_name}",
                            "description": "Module implementation progress and blockers",
                            "required": True,
                        }
                    ],
                    "constraints": [],
                    "acceptance_criteria": requirement_refs[:3],
                    "failure_handling": [
                        "Backflow to SOLUTION when module ownership becomes ambiguous.",
                        "Backflow to REQUIREMENTS when acceptance criteria are unstable.",
                    ],
                }
            )
        return contracts

    def build_data_flow(
        self, contracts: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        data_flow: list[dict[str, object]] = []
        for index, contract in enumerate(contracts, start=1):
            contract_name = str(contract.get("name", ""))
            if not contract_name:
                continue
            data_flow.append(
                {
                    "step": index,
                    "contract_name": contract_name,
                    "from": "Solution Engineer",
                    "to": ["System Designer", "Implementation Engineer"],
                    "trigger": "Solution state is ready for execution planning.",
                    "notes": "",
                }
            )
        return data_flow

    def build_mvp_plan(
        self,
        spec: dict[str, object],
        module_mapping: list[dict[str, object]],
    ) -> dict[str, object]:
        in_scope = self.dedupe_items(
            [
                str(item)
                for item in spec.get("functional_requirements", [])[:3]
                if self.normalize_text(str(item))
            ]
        )
        out_of_scope = self.dedupe_items(
            [
                f"Unresolved item: {item}"
                for item in spec.get("open_questions", [])
                if self.normalize_text(str(item))
            ]
        )
        milestones = [
            "Lock design contracts for the first deliverable.",
            "Implement at least one module with contract compliance.",
            "Run validation and record issue attribution in test_report.",
        ]
        first_module = ""
        if module_mapping:
            first_module = self.slugify_text(str(module_mapping[0].get("module", "")))
        first_deliverable = (
            f"Deliver implementation-ready design for {first_module}."
            if first_module
            else "Deliver implementation-ready design for the first solution module."
        )
        return {
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "milestones": milestones,
            "first_deliverable": first_deliverable,
        }
