from __future__ import annotations

from typing import Any

from .models import Stage, StageFlags


class StageEvaluator:
    def is_requirements_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        spec = states.get("spec", {})
        return bool(
            spec.get("project_goal")
            and spec.get("functional_requirements")
            and spec.get("acceptance_criteria")
        )

    def is_solution_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.is_requirements_ready(states):
            return False

        solution = states.get("solution", {})
        selected_stack = solution.get("selected_stack", {})
        module_mapping = solution.get("module_mapping", [])
        spec = states.get("spec", {})
        functional_requirements = spec.get("functional_requirements", [])

        has_core_backend = bool(selected_stack.get("backend"))

        stable_modules = [
            module
            for module in module_mapping
            if module.get("module") and module.get("responsibilities")
        ]
        covered_requirements = {
            requirement
            for module in stable_modules
            for requirement in module.get("covers_requirements", [])
            if requirement
        }

        return bool(
            has_core_backend
            and stable_modules
            and functional_requirements
            and covered_requirements
        )

    def is_design_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.is_solution_ready(states):
            return False

        design = states.get("system_design", {})
        project_structure = design.get("project_structure", {})
        modules = project_structure.get("modules", [])
        contracts = design.get("contracts", [])
        data_flow = design.get("data_flow", [])
        mvp_plan = design.get("mvp_plan", {})

        stable_contracts = [
            contract
            for contract in contracts
            if contract.get("name")
            and contract.get("producer")
            and contract.get("consumers")
            and contract.get("input")
            and contract.get("output")
        ]
        stable_contract_names = {
            contract["name"] for contract in stable_contracts if contract.get("name")
        }
        valid_data_flow = [
            step
            for step in data_flow
            if step.get("contract_name") in stable_contract_names
        ]

        return bool(
            modules
            and stable_contracts
            and valid_data_flow
            and mvp_plan.get("in_scope")
            and mvp_plan.get("first_deliverable")
        )

    def has_active_implementation(
        self, states: dict[str, dict[str, Any]]
    ) -> bool:
        if not self.is_design_ready(states):
            return False

        implementation_status = states.get("implementation_status", {})
        return bool(
            implementation_status.get("module_name")
            and implementation_status.get("implementation_status")
            in {"in_progress", "blocked", "done"}
        )

    def has_validation_context(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.has_active_implementation(states):
            return False

        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        return bool(
            implementation_status.get("implementation_status") == "done"
            and not implementation_status.get("blockers")
            and test_report.get("test_scope")
        )

    def is_done(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.has_validation_context(states):
            return False

        test_report = states.get("test_report", {})
        issues = test_report.get("issues", [])
        blocking_issue_exists = any(
            issue.get("status") in {"open", "confirmed"}
            and issue.get("severity") in {"high", "critical"}
            for issue in issues
        )

        return bool(
            test_report.get("result") == "pass" and not blocking_issue_exists
        )

    def evaluate_stage_flags(self, states: dict[str, dict[str, Any]]) -> StageFlags:
        requirements_ready = self.is_requirements_ready(states)
        solution_ready = requirements_ready and self.is_solution_ready(states)
        design_ready = solution_ready and self.is_design_ready(states)
        implementing_active = design_ready and self.has_active_implementation(states)
        testing_active = implementing_active and self.has_validation_context(states)
        done_ready = testing_active and self.is_done(states)

        return StageFlags(
            requirements_ready=requirements_ready,
            solution_ready=solution_ready,
            design_ready=design_ready,
            implementing_active=implementing_active,
            testing_active=testing_active,
            done_ready=done_ready,
        )

    def stage_from_flags(self, flags: StageFlags) -> Stage:
        if flags.done_ready:
            return Stage.DONE
        if flags.testing_active:
            return Stage.TESTING
        if flags.implementing_active:
            return Stage.IMPLEMENTATION
        if flags.design_ready:
            return Stage.DESIGN
        if flags.solution_ready:
            return Stage.SOLUTION
        if flags.requirements_ready:
            return Stage.REQUIREMENTS
        return Stage.INIT

    def compute_current_stage(
        self, states: dict[str, dict[str, Any]]
    ) -> Stage:
        return self.stage_from_flags(self.evaluate_stage_flags(states))

    def infer_source_stage(self, states: dict[str, dict[str, Any]]) -> Stage:
        computed_stage = self.compute_current_stage(states)
        if computed_stage in {
            Stage.TESTING,
            Stage.IMPLEMENTATION,
            Stage.DESIGN,
            Stage.SOLUTION,
        }:
            return computed_stage

        test_report = states.get("test_report", {})
        implementation_status = states.get("implementation_status", {})
        design = states.get("system_design", {})
        solution = states.get("solution", {})

        if (
            implementation_status.get("implementation_status") == "done"
            and (
                test_report.get("result") != "not_run"
                or bool(test_report.get("issues"))
            )
        ):
            return Stage.TESTING

        if (
            implementation_status.get("module_name")
            and implementation_status.get("implementation_status")
            in {"in_progress", "blocked", "done"}
        ):
            return Stage.IMPLEMENTATION

        if (
            design.get("project_structure", {}).get("modules")
            or design.get("contracts")
            or design.get("data_flow")
            or design.get("mvp_plan", {}).get("first_deliverable")
        ):
            return Stage.DESIGN

        selected_stack = solution.get("selected_stack", {})
        if (
            solution.get("module_mapping")
            or selected_stack.get("backend")
            or selected_stack.get("frontend")
            or selected_stack.get("agent_framework")
        ):
            return Stage.SOLUTION

        return computed_stage

    def apply_backflow_to_flags(
        self, flags: StageFlags, backflow_target: Stage
    ) -> StageFlags:
        resolved = StageFlags(
            requirements_ready=flags.requirements_ready,
            solution_ready=flags.solution_ready,
            design_ready=flags.design_ready,
            implementing_active=flags.implementing_active,
            testing_active=flags.testing_active,
            done_ready=flags.done_ready,
        )

        if backflow_target == Stage.REQUIREMENTS:
            resolved.solution_ready = False
            resolved.design_ready = False
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.SOLUTION:
            resolved.design_ready = False
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.DESIGN:
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.IMPLEMENTATION:
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        return resolved
