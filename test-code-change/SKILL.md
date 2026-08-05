---
name: test-code-change
description: "Risk-driven test design and verification for coding agents changing maintained code. Use when implementing, fixing, refactoring, deleting, migrating, or reviewing code to identify affected behavior, select sufficient scientific test methods, apply TDD where useful, execute affected regressions, evaluate changed-line and branch coverage, and report reproducible evidence and residual risk."
---

# Test Code Change

Prove a code change with the smallest test portfolio that can reliably expose its important failures. Optimize for defect detection and trustworthy evidence, not test count, ritual, or a coverage number.

Operate independently. Accept an existing contract, impact analysis, or test plan when available, but verify it against the repository. Derive any missing artifact from the request, diff, code, callers, tests, and project instructions.

## Operating Modes

Choose the mode implied by the request:

- **Implementation:** design tests, observe the required failures, change code, and execute verification.
- **Review:** inspect the change and existing evidence without editing; report concrete gaps and risks.
- **Blocked:** complete the analysis possible from source, identify missing evidence, and provide the exact discovered commands that remain to run.

Never claim that an unexecuted test passed. Never change production code in review mode.

## Workflow

### 1. Establish the Change Basis

Inspect the repository instructions, status, diff, comparison base, relevant implementation, callers, callees, tests, manifests, and CI configuration. Discover test and coverage commands from the repository; do not guess them.

Separate pre-existing failures and unrelated work from change-caused evidence. Classify each meaningful change as one or more of:

- added behavior
- modified behavior
- deleted behavior
- bug fix
- behavior-preserving refactor
- public contract or schema change
- migration or external-side-effect change

State the observable contract: inputs, outputs, preconditions, postconditions, state transitions, side effects, and declared error modes. Resolve material ambiguity before treating the test plan as complete.

### 2. Build the Impact Map

Trace changed symbols to direct callers, downstream dependencies, tests, and externally observable behavior. Include relevant indirect surfaces:

- public APIs, events, serialization, schemas, configuration, and CLI behavior
- persisted data, migrations, caches, queues, files, and remote services
- authorization, validation, secrets, and sensitive logging
- time, retries, idempotency, concurrency, ordering, and resource cleanup
- error propagation, fallback behavior, logs, metrics, and traces

Express each risk as:

> Because of **change**, **failure mode** may affect **surface**, supported by **repository evidence**.

Read [impact-analysis.md](references/impact-analysis.md) for the change-type probes, risk rubric, escalation rules, and residual-risk model. Do not rate risk from line count or intuition.

### 3. Design the Test Portfolio

For every material risk, record:

| Contract or risk | Test boundary | Method | Cases | Oracle | Expected evidence |
|---|---|---|---|---|---|

Choose the cheapest stable boundary that can observe the failure. Select methods from [test-method-selection.md](references/test-method-selection.md); do not mechanically require every test type.

Define each test as a reproducible experiment:

- **Hypothesis:** the observable behavior or invariant being tested.
- **Setup and controls:** the state, fixtures, clock, randomness, and external boundaries.
- **Stimulus:** the action or input.
- **Oracle:** the exact result, state, side effect, error, or signal that distinguishes success from failure.

Cover the relevant success path, boundaries, state transitions, and declared failures. Exclude impossible or contract-invalid cases unless validating rejection is itself required behavior.

### 4. Apply the TDD Micro-Cycle Where It Adds Signal

Use `RED -> GREEN -> REFACTOR -> TRIANGULATE`:

1. **RED:** make the next behavior fail for the intended reason, not because of syntax, fixture, or environment failure.
2. **GREEN:** implement the smallest behavior that satisfies the contract.
3. **REFACTOR:** improve structure only while the relevant tests remain green.
4. **TRIANGULATE:** add another representative, boundary, or failure example when one case could permit a false generalization.

Require observed red-to-green evidence for bug fixes. For behavior-preserving refactors, establish characterization or differential evidence before restructuring. For deletions, prove consumer migration, absence of stale references, and the intended compatibility or rejection behavior.

Allow an exploratory spike without test-first development only when the contract is still unknown. Do not treat spike code as production-ready evidence.

### 5. Execute Evidence from Narrow to Broad

Run the cheapest useful checks first:

1. targeted tests for the changed behavior
2. directly affected module or component suites
3. integration, contract, and critical journey tests required by the impact map
4. repository-required type, lint, build, and static checks
5. the full suite when required by the repository, justified by broad risk, or reasonably affordable

Do not run a broad suite as a substitute for missing targeted assertions. Do not stop after targeted tests when the impact map crosses a boundary.

### 6. Evaluate Test Quality and Coverage

Assert observable behavior, state, side effects, and error contracts. Mock only true external boundaries; do not mock away the behavior under test. Control time, randomness, network, shared state, and ordering where they affect reproducibility.

Honor existing line and branch coverage gates and never lower them. When repository tooling supports diff coverage, report changed executable lines and altered branches. Investigate every material uncovered change; either add a risk-justified test or explain why execution is unreachable or not behavior-bearing.

Do not invent a universal percentage. Coverage proves execution, not assertion effectiveness. For high-risk logic with a weak oracle, use selective mutation, differential, property, or fault-injection testing when supported and proportionate.

Treat difficult testing as a design signal, not automatic permission for a rewrite. Introduce only the smallest boundary the requested behavior genuinely needs.

### 7. Verify Failure Handling and Observability

When the impact map reaches these concerns, test them explicitly:

- errors preserve type, context, and actionable failure behavior instead of becoming silent defaults
- partial failures do not leave invalid state or leaked resources
- retries, timeouts, and duplicate delivery preserve declared invariants
- logs and telemetry appear at the intended boundary or state transition
- sensitive values are absent from logs, errors, snapshots, and fixtures
- log level, correlation fields, and failure details match the repository convention

Do not add logs or error wrappers merely to satisfy a checklist. Verify only behavior relevant to the change and its risks.

## Completion Standard

Call verification sufficient only when:

- every changed observable contract maps to evidence or an explicit no-test rationale
- every high or critical failure mode has direct evidence at a boundary capable of exposing it
- affected consumers and cross-boundary behavior have the required regression coverage
- altered conditions, executable lines, and failure paths have no unexplained material gap
- tests can fail for the defect they claim to detect
- actual command results are distinguished from static analysis and unexecuted recommendations
- remaining uncertainty is recorded as residual risk

Use [evidence-report-template.md](references/evidence-report-template.md) for substantial changes. Keep the user-facing handoff compact, but retain the reasoning needed to audit the conclusion.

Never describe testing as absolutely complete. Bound the claim to the discovered impact map, executed environment, and observed evidence.
