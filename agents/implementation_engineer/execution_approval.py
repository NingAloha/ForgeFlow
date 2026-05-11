from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _canonical_contract_payload(contract: dict[str, Any]) -> dict[str, Any]:
    """Normalize contract dict for stable hashing."""
    return dict(contract)


def _canonical_patch_draft(patch_draft: str) -> str:
    return "\n".join(line.rstrip() for line in patch_draft.strip().splitlines())


def build_contract_fingerprint(contract: dict[str, Any], patch_draft: str) -> str:
    canonical_contract = _canonical_contract_payload(contract)
    contract_json = json.dumps(canonical_contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    canonical_draft = _canonical_patch_draft(patch_draft)
    payload = f"{contract_json}\n---PATCH_DRAFT---\n{canonical_draft}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_pending_approval(contract: dict[str, Any], patch_draft: str) -> dict[str, Any]:
    return {
        "approval_status": "pending",
        "contract_hash": build_contract_fingerprint(contract, patch_draft),
        "contract_version": str(contract.get("execution_contract_version", "")),
        "target_module": str(contract.get("target_module", "")),
        "review_decision": "",
        "review_reason": "",
        "approved_at": "",
        "approved_by": "",
        "stale": False,
    }


def approve_execution_contract(
    approval: dict[str, Any],
    contract: dict[str, Any],
    patch_draft: str,
    approved_by: str = "user",
) -> dict[str, Any]:
    expected_hash = str(approval.get("contract_hash", ""))
    current_hash = build_contract_fingerprint(contract, patch_draft)
    if expected_hash != current_hash:
        updated = dict(approval)
        updated["approval_status"] = "invalidated"
        updated["review_decision"] = ""
        updated["review_reason"] = "contract changed before approval"
        updated["approved_at"] = ""
        updated["approved_by"] = ""
        updated["stale"] = True
        updated["contract_hash"] = current_hash
        updated["contract_version"] = str(contract.get("execution_contract_version", ""))
        updated["target_module"] = str(contract.get("target_module", ""))
        return updated

    updated = dict(approval)
    updated["approval_status"] = "approved"
    updated["review_decision"] = "approved"
    updated["review_reason"] = ""
    updated["approved_at"] = datetime.now(timezone.utc).isoformat()
    updated["approved_by"] = approved_by
    updated["stale"] = False
    updated["contract_version"] = str(contract.get("execution_contract_version", ""))
    updated["target_module"] = str(contract.get("target_module", ""))
    return updated


def reject_execution_contract(approval: dict[str, Any], reason: str) -> dict[str, Any]:
    updated = dict(approval)
    updated["approval_status"] = "rejected"
    updated["review_decision"] = "rejected"
    updated["review_reason"] = reason.strip()
    updated["approved_at"] = ""
    updated["approved_by"] = ""
    updated["stale"] = False
    return updated


def invalidate_execution_approval(approval: dict[str, Any], reason: str) -> dict[str, Any]:
    updated = dict(approval)
    updated["approval_status"] = "invalidated"
    updated["review_decision"] = ""
    updated["review_reason"] = reason.strip()
    updated["approved_at"] = ""
    updated["approved_by"] = ""
    updated["stale"] = True
    return updated


def is_approval_stale(
    approval: dict[str, Any],
    contract: dict[str, Any],
    patch_draft: str,
) -> bool:
    expected_hash = str(approval.get("contract_hash", ""))
    current_hash = build_contract_fingerprint(contract, patch_draft)
    return expected_hash != current_hash
