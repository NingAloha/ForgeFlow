# Runtime Observation: Testing Block Authority

## Context
ForgeFlow is currently in Phase A:
- human-authoritative overall
- runtime-assisted governance
- no automatic rollback
- no real mutation runtime
- no Git checkpointing

## Before
- Testing failures could backflow when a rollback target was determined.
- But when no backflow target existed, transition evidence could collapse into a generic “stay/no invariant satisfied” diagnostic.
- Environment/tooling failures were not explicitly represented as “block without rollback”, and could be hard to distinguish from implementation failure in the transition meaning.

## Change
ForgeFlow now makes a small deterministic authority decision at the Testing boundary, based on structured test evidence:
- environment/tooling failure → `STAY(TESTING)`, blocked, with explicit no-rollback evidence
- implementation-attributed failure → backflow target = `IMPLEMENTATION`
- missing hard test evidence → testing cannot be marked done
- `STAY` decisions now preserve backflow/block evidence when it exists (instead of collapsing into a generic “stay”)

## Why This Matters
This is the first minimal “authority surface” that goes beyond recording artifacts:
- the runtime preserves transition meaning deterministically and makes it inspectable
- rollback ambiguity is reduced (environment failure no longer looks like implementation failure)
- the Testing boundary can be governed by hard evidence fields rather than narrative assessment

## Evidence
Tests added for deterministic behavior:
- `test_testing_environment_failure_stays_put_without_rollback`
- `test_testing_environment_failure_stays_on_testing_with_evidence`
- `test_is_done_requires_hard_test_evidence_fields`

Validation:
- `ruff check .`
- `pytest -q`

## Boundaries
This does not implement:
- automatic rollback
- implementation invalidation propagation
- generalized attribution taxonomy
- Git checkpointing
- autonomous progression
- command execution or patch apply

## Remaining Questions
- Should environment failure detection remain keyword-based?
- Should block decisions get a dedicated structured field later?
- Should implementation-attributed failures eventually mark implementation state invalid, rather than only suggesting backflow?
- What tiny real scenario should be used to manually observe this behavior end-to-end?

