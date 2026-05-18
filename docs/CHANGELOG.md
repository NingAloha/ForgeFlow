# Changelog

This changelog records notable changes for ForgeFlow runtime releases.

Note: This file lives under `docs/` because `track/**` branches are path-guarded; repository-root docs files (other than `README*`) are intentionally restricted.

## v0.2.1 (2026-05-18)

Stabilization release focused on governed materialization reliability, attempt lifecycle semantics, and replay/gate observability. No mutation semantics are introduced in this release.

- Define `started` / `failed` / `completed` materialization attempt lifecycle semantics.
- Block incomplete materialization attempts (`status=started`) to avoid ambiguity.
- Allow retry after failed materialization attempts (`status=failed`).
- Make completed reruns idempotent (no-op) with fixed CLI messaging.
- Expose materialization observability in `--replay-run` and `--execution-gate`.
- Preserve the mutation-disabled runtime boundary.

## v0.2.0-governed-materialization (2026-05-18)

Initial governed sandbox materialization milestone (mutation disabled).

- Introduce gated materialization preview write-path (`--materialize-preview`).
- Record run-scoped execution preview artifacts and append runtime events for auditability.
- Add replay rendering so materialization preview can be explained from runtime artifacts.

