from __future__ import annotations

from .se.manifest import SEProfileManifest, get_se_manifest


def get_profile_manifest(profile_name: str) -> SEProfileManifest:
    """
    Return a declared workflow manifest for a profile.

    This function is fail-closed: unknown profiles raise immediately.
    It must not return a shared mutable singleton.
    """

    name = str(profile_name).strip()
    if name != "se":
        raise ValueError(f"Unknown profile: {name}")

    # `get_se_manifest()` may be cached; always return a defensive deep copy.
    return get_se_manifest().model_copy(deep=True)
