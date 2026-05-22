from __future__ import annotations

import pytest

from forgeflow.profiles.registry import get_profile_manifest


def test_profile_registry_returns_manifest_copy() -> None:
    m1 = get_profile_manifest("se")
    m2 = get_profile_manifest("se")
    assert m1 is not m2

    m1.artifact_keys.append("x")
    assert "x" not in m2.artifact_keys


def test_profile_registry_unknown_profile_fail_closed() -> None:
    with pytest.raises(ValueError):
        get_profile_manifest("unknown")

