#!/usr/bin/env bash
set -euo pipefail

branch="${BRANCH_NAME:-${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}}"
base_ref="${BASE_REF:-${GITHUB_BASE_REF:-origin/main}}"

if [[ -z "${branch}" ]]; then
  echo "branch_path_guard: skip (branch name unavailable)"
  exit 0
fi

if [[ "${branch}" == "main" ]]; then
  echo "branch_path_guard: skip on main"
  exit 0
fi

if [[ "${branch}" != track/* ]]; then
  echo "branch_path_guard: skip (non-track branch: ${branch})"
  exit 0
fi

if ! git rev-parse --verify "${base_ref}" >/dev/null 2>&1; then
  if git rev-parse --verify "origin/main" >/dev/null 2>&1; then
    base_ref="origin/main"
  else
    base_ref="$(git merge-base HEAD main 2>/dev/null || true)"
  fi
fi

if [[ -z "${base_ref}" ]]; then
  echo "branch_path_guard: unable to resolve base ref"
  exit 1
fi

changed_files=()
while IFS= read -r file; do
  [[ -n "${file}" ]] || continue
  changed_files+=("${file}")
done < <(git diff --name-only "${base_ref}...HEAD")

if [[ ${#changed_files[@]} -eq 0 ]]; then
  echo "branch_path_guard: no changed files"
  exit 0
fi

is_allowed_for_branch() {
  local file="$1"
  case "${branch}" in
    track/orchestrator)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == tests/unit/orchestrator/* ]] && return 0
      ;;
    track/implementation-governance)
      [[ "${file}" == agents/implementation_engineer/* ]] && return 0
      [[ "${file}" == schemas/implementation.py ]] && return 0
      [[ "${file}" == tests/unit/agents/test_implementation_engineer.py ]] && return 0
      [[ "${file}" == tests/unit/agents/test_execution_* ]] && return 0
      ;;
    track/testing-semantics)
      [[ "${file}" == agents/test_validation_engineer/* ]] && return 0
      [[ "${file}" == tests/unit/agents/test_test_validation_engineer.py ]] && return 0
      [[ "${file}" == tests/unit/agents/test_agent_integration.py ]] && return 0
      ;;
    track/tui-observability)
      [[ "${file}" == tui/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/test_tui.py ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/test_status_overview.py ]] && return 0
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == forgeflow/__init__.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/__init__.py ]] && return 0
      [[ "${file}" == pyproject.toml ]] && return 0
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      ;;
    track/runtime-replay-foundation)
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/test_main.py ]] && return 0
      ;;
    track/runtime-event-log)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/test_main.py ]] && return 0
      [[ "${file}" == docs/runtime-events.md ]] && return 0
      ;;
    track/runtime-run-index)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/orchestrator/test_core.py ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/test_status_overview.py ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/runtime-index-repair)
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/review-decision-artifacts)
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/review-approval-bridge)
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/execution-gate-diagnostics)
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/execution-gate-diagnostics-v2)
      [[ "${file}" == main.py ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/lineage-invalidation-metadata)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/orchestrator/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/needs-rerun-diagnostics)
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/artifact-lineage-foundation)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/orchestrator/test_core.py ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/human-workflow-semantics)
      [[ "${file}" == agents/orchestrator/* ]] && return 0
      [[ "${file}" == forgeflow/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/runtime/* ]] && return 0
      [[ "${file}" == tests/unit/orchestrator/* ]] && return 0
      [[ "${file}" == tests/unit/entrypoints/* ]] && return 0
      [[ "${file}" == docs/* ]] && return 0
      ;;
    track/docs-review)
      [[ "${file}" == docs/* ]] && return 0
      [[ "${file}" == runs/manual_reviews/* ]] && return 0
      [[ "${file}" == README.md || "${file}" == README_EN.md ]] && return 0
      ;;
  esac

  [[ "${file}" == docs/* ]] && return 0
  [[ "${file}" == README.md || "${file}" == README_EN.md ]] && return 0
  [[ "${file}" == .github/workflows/* ]] && return 0
  [[ "${file}" == scripts/branch_path_guard.sh ]] && return 0
  return 1
}

violations=()
for file in "${changed_files[@]}"; do
  if ! is_allowed_for_branch "${file}"; then
    violations+=("${file}")
  fi
done

if [[ ${#violations[@]} -gt 0 ]]; then
  echo "branch_path_guard: blocked on branch ${branch}"
  echo "These files are outside the allowed scope:"
  for file in "${violations[@]}"; do
    echo " - ${file}"
  done
  echo "See docs/branch-boundaries.md for policy."
  exit 1
fi

echo "branch_path_guard: passed for ${branch}"
