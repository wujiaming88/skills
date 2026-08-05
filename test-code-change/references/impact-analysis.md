# Change Impact and Risk Analysis

Use this reference to build the mandatory impact table and assign a risk level to every material failure mode. Base every entry on repository evidence.

## Contents

- [Change-Type Probes](#change-type-probes)
- [Impact Map](#impact-map)
- [Risk Statement](#risk-statement)
- [Risk Dimensions](#risk-dimensions)
- [Risk Classification](#risk-classification)
- [Inherent and Residual Risk](#inherent-and-residual-risk)
- [Verification Intensity](#verification-intensity)

## Change-Type Probes

### Added Behavior

- Identify every path that can activate the behavior.
- Check defaults, disabled states, invalid input, and interaction with existing branches.
- Find newly reachable side effects, dependencies, permissions, resource use, and operational signals.

### Modified Behavior

- State the old and new observable contracts.
- Search direct and transitive consumers of the changed symbol or data.
- Identify preserved behavior that still requires regression evidence.

### Deleted Behavior

- Search callers, exports, registries, configuration, examples, fixtures, and tests.
- Verify the intended result for old consumers: migration, compatibility response, explicit rejection, or removal.
- Check orphaned state, data, flags, telemetry, and dependencies.

### Bug Fix

- Reconstruct the failing input, state, and mechanism.
- Capture direct RED evidence when reproducible; otherwise identify the strongest mechanism-level substitute.
- Search sibling paths that share the same faulty assumption.

### Behavior-Preserving Refactor

- Establish the behavior baseline before restructuring.
- Prefer characterization, differential, invariant, or existing contract tests.
- Treat changed external behavior as a separate change.

### Contract, Schema, or Migration Change

- Identify producers, consumers, versions, rollout order, and rollback behavior.
- Verify forward and backward compatibility where required.
- Test partial, repeated, interrupted, and mixed-version operation when applicable.

### Dependency or Runtime Upgrade

- Inspect direct and transitive version changes, release notes, runtime constraints, and lockfiles.
- Identify changed defaults, APIs, data formats, performance, security posture, and platform support.
- Exercise the owned integration boundary instead of relying only on dependency tests.

## Impact Map

Inspect each category before excluding it:

| Surface | Evidence to inspect |
|---|---|
| Code | definitions, callers, callees, implementations, exports |
| Behavior | user journeys, state transitions, business rules |
| Contracts | API, CLI, event, schema, serialization, configuration |
| Data | persistence, migrations, cache, queue, file formats |
| Effects | network, filesystem, process, notification, billing |
| Safety | validation, authorization, abuse, secrets, sensitive data |
| Reliability | timeout, retry, idempotency, concurrency, cleanup |
| Performance | latency, throughput, capacity, resource consumption, leaks |
| Dependencies | direct/transitive upgrades, runtime, platform, changed defaults |
| Observability | errors, logs, metrics, traces, alerts |
| Delivery | feature flags, compatibility, rollout, rollback |

Record unknown edges explicitly. An unresolved caller, contract, runtime assumption, capacity limit, or dependency effect is an unknown risk input.

## Risk Statement

Write one falsifiable statement per failure mode:

> Because of **specific change**, **specific failure** may affect **specific surface**, supported by **file, symbol, caller, contract, measurement, or runtime evidence**.

Split risks that require different tests. Do not use vague labels such as "large change" or "may cause issues."

## Risk Dimensions

Assess four dimensions:

| Dimension | Low | Medium | High | Severe |
|---|---|---|---|---|
| Impact | local internal defect | one feature degrades | public behavior or data is wrong | security, money, data loss, outage |
| Exposure | rare internal path | limited module or cohort | common path or many consumers | default/public path at broad scale |
| Change hazard | mechanical and checked | simple branch or validation | state, IO, compatibility | concurrency, migration, auth, distributed effects |
| Detection and recovery difficulty | immediate and reversible | stable detection or rollback | delayed, partial, or costly | silent, irreversible, or hard to diagnose |

## Risk Classification

Apply these rules in order:

1. Assign **Critical** to security compromise, financial corruption, data loss, or irreversible migration.
2. Otherwise assign **High** when any dimension is Severe or at least two dimensions are High.
3. Otherwise assign **Medium** when any dimension is High or Medium, or the change crosses modules, a public contract, or external IO.
4. Assign **Low** only when every dimension is Low and direct repository evidence supports that assessment.
5. Raise the result one level for each material unknown, capped at Critical. Consolidate related unknowns when they represent the same evidence gap.

Use the order `Low -> Medium -> High -> Critical`. Record the dimension values, applied rule, and unknowns so another reviewer can reproduce the classification.

## Inherent and Residual Risk

Keep two ratings:

- **Inherent risk:** risk before new verification and controls.
- **Residual risk:** risk remaining after executed evidence and verified controls.

Testing can reduce uncertainty and improve detection confidence; it cannot reduce the impact severity of the failure itself. Never revise the Impact dimension downward merely because tests pass.

Every residual-risk downgrade must cite specific executed evidence or a verified control, such as:

- all material consumers identified
- an effective regression, contract, integration, performance, or security test executed
- a type or schema check that prevents the failure
- a verified compatibility layer, feature flag, or rollback path
- mutation or fault injection showing that the oracle detects the mechanism

Do not downgrade risk because code looks simple or aggregate coverage is high. Preserve any untested environment, scale, timing, or consumer uncertainty in the residual-risk statement.

## Verification Intensity

Use the level as the minimum evidence intensity:

| Level | Minimum response |
|---|---|
| Low | direct targeted evidence plus repository-required checks |
| Medium | targeted evidence, relevant boundaries/errors, and affected consumers |
| High | Medium plus cross-boundary, failure-path, and coverage-gap evidence |
| Critical | High plus critical journey, recovery/fault evidence, independent scrutiny, and explicit residual risk |

Escalate the test boundary when a cheaper test cannot expose the stated failure. Never use broad execution as a substitute for a discriminating oracle.
