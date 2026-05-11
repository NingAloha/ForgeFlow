from __future__ import annotations

from ..common.text import TextHelper


class ImplementationPlanningMixin(TextHelper):
    RESERVED_GENERIC_MODULES = {"core", "utils", "app"}
    EXECUTE_MODE_BLOCKER = (
        "code execution mode is not enabled; missing execution safety boundary"
    )
    EXECUTE_MODE_LIMITATIONS = [
        "workspace sandbox: workspace_root must be explicit and execution must stay inside sandbox",
        "allowed paths (write): src/<module>/ and tests/<module>/",
        "allowed paths (read): spec, solution, system_design, implementation_status, test_report",
        "denied paths (write): .git/, .env, secrets/*, ~/*, /, pyproject.toml, .github/",
        "allowed commands: python -m pytest tests/<module>; python -m unittest discover -s tests -p 'test_*.py'; ruff check .",
        "denied command examples: rm -rf, curl | bash, pip install, sudo, chmod -R, git push",
        "retry limit: max_retries=1",
        "patch preview required: files_to_create, files_to_modify, files_to_delete, rationale, risk, test_plan",
        "rollback policy required: pre_patch_snapshot, patch_id, rollback_available=true",
        "execution report required: module, patch_id, files_modified, commands_run, test_results, blockers, next_action",
    ]
    EXECUTE_MODE_NO_MODULE_BLOCKER = "no design module available for patch draft"
    EXECUTION_CONTRACT_VERSION = "v1"

    def resolve_implementation_mode(
        self,
        current_state: dict[str, object],
        metadata: dict[str, object],
    ) -> str:
        raw_mode = (
            str(metadata.get("implementation_mode", "")).strip().lower()
            or str(current_state.get("implementation_mode", "")).strip().lower()
        )
        if raw_mode == "execute":
            return "execute"
        return "handoff"

    def build_execution_disabled_status(
        self,
        current_state: dict[str, object],
        design: dict[str, object],
    ) -> dict[str, object]:
        modules = self.get_design_modules(design)
        primary_module = self.select_primary_module_name(current_state, modules)
        files_touched: list[str] = []
        tests_added_or_updated: list[str] = []
        preview_notes: list[str] = []
        blockers = [
            self.EXECUTE_MODE_BLOCKER,
            "patch preview generated; no mutation performed",
            "single-module patch draft generated; no mutation performed",
        ]

        if not primary_module:
            blockers.append(self.EXECUTE_MODE_NO_MODULE_BLOCKER)
        else:
            files_touched.append(
                f"module={primary_module}; operation=create_only; files_to_create=[src/{primary_module}/README.md | tests/{primary_module}/README.md]; files_to_modify=[]; files_to_delete=[]"
            )
            tests_added_or_updated.append(
                f"module={primary_module}; test_plan=[pytest tests/{primary_module}]"
            )
            preview_notes.append(
                " ".join(
                    [
                        f"module={primary_module};",
                        "rationale=prepare minimal module scaffold aligned with design handoff;",
                        "risk=module boundary mismatch or contract interpretation drift;",
                        "rollback_note=use pre_patch_snapshot and patch_id to revert if future execution is enabled;",
                    ]
                )
            )
        return {
            **current_state,
            "module_name": primary_module,
            "implementation_status": "blocked",
            "files_touched": files_touched,
            "tests_added_or_updated": tests_added_or_updated,
            "contract_compliance": False,
            "known_limitations": list(self.EXECUTE_MODE_LIMITATIONS) + preview_notes,
            "blockers": blockers,
            "workspace_path": str(current_state.get("workspace_path", "")),
            "commands_executed": [],
            "artifacts_generated": [],
            "suggested_test_command": [],
        }

    def build_execution_contract_lines(self, module_name: str) -> list[str]:
        lines = [
            f"execution_contract_version={self.EXECUTION_CONTRACT_VERSION}",
            "execution_intent=review_only",
            "mutation_performed=false",
        ]
        if not module_name:
            return lines
        lines.extend(
            [
                f"target_module={module_name}",
                "plan_type=patch_preview+patch_draft",
                f"create=[src/{module_name}/README.md, tests/{module_name}/README.md]",
                "modify=[]",
                "delete=[]",
                "rationale=prepare reviewable implementation intent from design without mutation",
                "risk=contract drift or module-boundary mismatch before real execution",
                f"test_plan=[pytest tests/{module_name}]",
                "rollback_expectation=pre_patch_snapshot+patch_id+rollback_available",
            ]
        )
        return lines

    def build_single_module_patch_draft(self, module_name: str) -> str:
        if not module_name:
            return ""
        return "\n".join(
            [
                f"diff --git a/src/{module_name}/README.md b/src/{module_name}/README.md",
                "new file mode 100644",
                "--- /dev/null",
                f"+++ b/src/{module_name}/README.md",
                "@@",
                f"+# {module_name}",
                "+",
                "+## Contract Source",
                "+- system_design.contracts",
                "+",
                "+## Implementation Checklist",
                "+- Follow design handoff checklist for this module",
                "+",
                "+## Done Criteria",
                "+- Handoff alignment validated",
                "",
                f"diff --git a/tests/{module_name}/README.md b/tests/{module_name}/README.md",
                "new file mode 100644",
                "--- /dev/null",
                f"+++ b/tests/{module_name}/README.md",
                "@@",
                f"+# {module_name} test plan",
                "+",
                "+## Suggested Tests",
                f"+- pytest tests/{module_name}",
            ]
        )

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
