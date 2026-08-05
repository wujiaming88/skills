# Change Impact and Risk Analysis

Use this reference to derive a testable impact map and calibrate verification effort. Base every conclusion on repository evidence.

## Contents

- [Change-Type Probes](#change-type-probes)
- [Impact Map](#impact-map)
- [Risk Statement](#risk-statement)
- [Risk Dimensions](#risk-dimensions)
- [Inherent and Residual Risk](#inherent-and-residual-risk)
- [Test Response by Level](#test-response-by-level)

## Change-Type Probes

### Added Behavior

- Identify every path that can activate the behavior.
- Check defaults, disabled states, invalid input, and interaction with existing branches.
- Find newly reachable side effects, dependencies, permissions, and operational signals.

### Modified Behavior

- State the old and new observable contracts.
- Search direct and transitive consumers of the changed symbol or data.
- Identify preserved behavior that still requires regression evidence.

### Deleted Behavior

- Search callers, exports, registries, configuration, documentation examples, fixtures, and tests.
- Verify the intended result for old consumers: migration, compatibility response, explicit rejection, or removal.
- Check orphaned state, data, flags, telemetry, and dependencies.

### Bug Fix

- Reconstruct the failing input, state, and mechanism.
- Capture a regression that fails for that mechanism before the fix.
- Search sibling paths that share the same faulty assumption.

### Behavior-Preserving Refactor

- Establish the behavior baseline before restructuring.
- Prefer characterization, differential, invariant, or existing contract tests.
- Treat changed external behavior as a separate change, not part of the refactor proof.

### Contract, Schema, or Migration Change

- Identify producers, consumers, versions, rollout order, and rollback behavior.
- Verify forward and backward compatibility where the release model requires it.
- Test partial, repeated, interrupted, and mixed-version operation when applicable.

## Impact Map

Trace only relevant edges, but inspect each category before excluding it:

| Surface | Evidence to inspect |
|---|---|
| Code | definitions, callers, callees, implementations, exports |
| Behavior | user journeys, state transitions, business rules |
| Contracts | API, CLI, event, schema, serialization, configuration |
| Data | persistence, migrations, cache, queue, file formats |
| Effects | network, filesystem, process, notification, billing |
| Safety | validation, authorization, secrets, sensitive data |
| Reliability | timeout, retry, idempotency, concurrency, cleanup |
| Observability | errors, logs, metrics, traces, alerts |
| Delivery | feature flags, compatibility, rollout, rollback |

Record unknown edges explicitly. An unresolved caller, contract, or runtime assumption prevents a low-risk rating.

## Risk Statement

Write one falsifiable statement per failure mode:

> Because of **specific change**, **specific failure** may affect **specific surface**, supported by **file, symbol, caller, contract, or runtime evidence**.

Split risks that require different tests. Do not use vague labels such as "large change" or "may cause issues."

## Risk Dimensions

Assess four dimensions qualitatively:

| Dimension | Low | Medium | High | Severe |
|---|---|---|---|---|
| Impact | local internal defect | one feature degrades | public behavior or data is wrong | security, money, data loss, outage |
| Exposure | rare internal path | limited module or cohort | common path or many consumers | default/public path at broad scale |
| Change hazard | mechanical and checked | simple branch or validation | state, IO, compatibility | concurrency, migration, auth, distributed effects |
| Detection and recovery difficulty | immediate and reversible | stable detection or rollback | delayed, partial, or costly | silent, irreversible, or hard to diagnose |

Use these deterministic classification rules:

- Classify security compromise, data loss, financial corruption, authorization bypass, or irreversible migration as **Critical**.
- Classify any Severe dimension, or two High dimensions, as at least **High**.
- Classify cross-module state, external IO, or public-contract changes as at least **Medium**.
- Classify a change as **Low** only when it is mechanical and compiler, type-system, or direct test evidence covers the affected behavior.
- Raise the rating one level for an unverified assumption, unknown consumer, missing environment, or unavailable required test.

Do not multiply dimension scores. Arithmetic can hide low-probability catastrophic failures and create false precision.

## Inherent and Residual Risk

Keep two ratings:

- **Inherent risk:** risk before new verification and controls.
- **Residual risk:** risk remaining after executed tests and verified controls.

Lower risk only with relevant evidence, such as:

- all material consumers identified
- an effective regression, contract, or integration test executed
- a type or schema check that prevents the failure
- a verified compatibility layer, feature flag, or rollback path
- mutation or fault injection showing the oracle detects the failure

Do not lower risk because code looks simple or aggregate coverage is high.

## Test Response by Level

Use the level to set a minimum response, then adapt to the failure mode:

| Level | Minimum response |
|---|---|
| Low | targeted proof plus repository-required static checks |
| Medium | targeted, boundary/error cases, and affected suite |
| High | Medium plus relevant integration/contract/failure-path evidence and coverage-gap review |
| Critical | High plus critical journey, fault or recovery evidence, independent scrutiny, and explicit residual risk |

Escalate verification when the cheapest test boundary cannot expose the stated failure.
