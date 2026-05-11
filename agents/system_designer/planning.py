from __future__ import annotations

from ..common.text import TextHelper


class SystemDesignPlanningMixin(TextHelper):
    def _normalize_module_name(self, value: str) -> str:
        return self.slugify_text(value) or "workflow_module"

    def _module_context(
        self, module: dict[str, object]
    ) -> tuple[str, list[str], list[str], str]:
        module_name = self._normalize_module_name(str(module.get("module", "")))
        requirements = [
            self.sentence_case(str(item))
            for item in module.get("covers_requirements", [])
            if self.normalize_text(str(item))
        ]
        responsibilities = [
            self.sentence_case(str(item))
            for item in module.get("responsibilities", [])
            if self.normalize_text(str(item))
        ]
        tech_note = self.normalize_text(str(module.get("tech_note", "")))
        return module_name, requirements, responsibilities, tech_note

    def build_project_structure(
        self, module_mapping: list[dict[str, object]]
    ) -> dict[str, list[str]]:
        module_names = sorted(
            {
                self._normalize_module_name(str(module.get("module", "")))
                for module in module_mapping
                if self.normalize_text(str(module.get("module", "")))
            }
        )
        directories = [
            "src/",
            "tests/",
            "contracts/",
            "docs/",
            "state/",
        ]
        directories.extend(f"src/{module}/" for module in module_names)
        directories.extend(f"tests/{module}/" for module in module_names)
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
            module_name, requirement_refs, responsibilities, tech_note = (
                self._module_context(module)
            )
            if not module_name:
                continue
            contract_name = f"solution_to_{module_name}_implementation"
            requirement_text = (
                "; ".join(requirement_refs[:2]) or "mapped requirement scope"
            )
            responsibility_text = (
                "; ".join(responsibilities[:2]) or "mapped module responsibility"
            )
            tech_context = tech_note or "python cli workflow"
            contracts.append(
                {
                    "name": contract_name,
                    "contract_type": "state_handoff",
                    "producer": "Solution Engineer",
                    "consumers": ["System Designer", "Implementation Engineer"],
                    "input": [
                        {
                            "name": f"solution.module_mapping[{module_name}]",
                            "description": (
                                "Module boundary and scope for "
                                f"{module_name}: {responsibility_text}"
                            ),
                            "required": True,
                        },
                        {
                            "name": "spec.functional_requirements",
                            "description": (
                                "Requirement references consumed by this module: "
                                f"{requirement_text}"
                            ),
                            "required": True,
                        },
                    ],
                    "output": [
                        {
                            "name": f"implementation_status.{module_name}",
                            "description": (
                                "Implementation status for this module, including "
                                "files_touched, tests_added_or_updated, and contract_compliance."
                            ),
                            "required": True,
                        },
                        {
                            "name": "test_report",
                            "description": (
                                "Validation evidence for mapped requirements and module output semantics."
                            ),
                            "required": True,
                        },
                    ],
                    "constraints": [
                        "Local CLI execution only; no Web UI or backend service in this design scope.",
                        "Input is markdown file content from local path; design must tolerate missing or irregular headings.",
                        f"Module technical context: {tech_context}",
                    ],
                    "acceptance_criteria": requirement_refs[:3],
                    "failure_handling": [
                        "input_errors: required inputs are missing, malformed, or semantically incomplete for module handoff.",
                        "processing_errors: module workflow cannot complete required transformation from input to planned output.",
                        "output_errors: generated status or validation evidence does not satisfy mapped acceptance criteria.",
                        "user_fixable: missing requirement detail or scope ambiguity can be clarified by user response.",
                        "retryable: transient dependency or environment instability allows re-run after context is unchanged.",
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
            contract_name_lower = contract_name.lower()
            if "markdown" in contract_name_lower:
                trigger = "CLI receives markdown input and parsing context is ready."
                notes = "Parse markdown structure and normalize sections for downstream summarization."
            elif "summary" in contract_name_lower or "extractor" in contract_name_lower:
                trigger = "Parsed markdown sections are available for key-point and action-item extraction."
                notes = "Transform normalized sections into title/key points/action items output semantics."
            else:
                trigger = "Module handoff prerequisites are available from solution/spec contexts."
                notes = "Complete module-level processing and prepare validation-ready status outputs."
            data_flow.append(
                {
                    "step": index,
                    "contract_name": contract_name,
                    "from": "Solution Engineer",
                    "to": ["System Designer", "Implementation Engineer"],
                    "trigger": trigger,
                    "notes": notes,
                }
            )
        return data_flow

    def build_mvp_plan(
        self,
        spec: dict[str, object],
        module_mapping: list[dict[str, object]],
    ) -> dict[str, object]:
        in_scope: list[str] = []
        for module in module_mapping:
            module_name, requirement_refs, responsibilities, _ = self._module_context(
                module
            )
            top_req = requirement_refs[0] if requirement_refs else "mapped requirement"
            top_resp = (
                responsibilities[0] if responsibilities else "mapped responsibility"
            )
            in_scope.append(f"{module_name}: {top_req}; execution intent: {top_resp}")
        in_scope = self.dedupe_items(in_scope[:4])
        out_of_scope = self.dedupe_items(
            [
                f"Unresolved item: {item}"
                for item in spec.get("open_questions", [])
                if self.normalize_text(str(item))
            ]
        )
        out_of_scope.extend(
            [
                "No Web UI design in this iteration.",
                "No persistent database service design in this iteration.",
                "No background worker or API service design in this iteration.",
            ]
        )
        out_of_scope = self.dedupe_items(out_of_scope)
        first_module = ""
        if module_mapping:
            first_module = self._normalize_module_name(
                str(module_mapping[0].get("module", ""))
            )
        milestones = [
            (
                f"Implement module {first_module or 'first_module'} with contract-compliant "
                "implementation_status outputs."
            ),
            "Run unittest discover command for CLI flow and record mapped validation outcomes.",
            "Confirm test_report links failures to input_errors/processing_errors/output_errors semantics.",
        ]
        first_deliverable = (
            f"Deliver implementation-ready handoff for module {first_module}: "
            "module boundary, constraints, failure semantics, and validation gate."
            if first_module
            else "Deliver implementation-ready handoff for the first mapped solution module."
        )
        return {
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "milestones": milestones,
            "first_deliverable": first_deliverable,
        }
