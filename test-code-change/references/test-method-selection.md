# Scientific Test Method Selection

Choose methods from the failure model and observable contract. Prefer the smallest portfolio that can falsify the important claims.

## Contents

- [Define a Valid Test](#define-a-valid-test)
- [Choose the Test Boundary](#choose-the-test-boundary)
- [Choose the Design Method](#choose-the-design-method)
- [Use Test Doubles Safely](#use-test-doubles-safely)
- [Apply TDD Deliberately](#apply-tdd-deliberately)
- [Design Cases Efficiently](#design-cases-efficiently)
- [Assess the Oracle](#assess-the-oracle)

## Define a Valid Test

For each case, specify:

1. **Hypothesis:** observable behavior or invariant.
2. **Setup and controls:** state, fixtures, clock, randomness, dependencies, and load.
3. **Stimulus:** input or action.
4. **Oracle:** exact value, state, side effect, error, timing bound, resource bound, or signal.
5. **Evidence:** reproducible command and observed result.

A test without a discriminating oracle is execution, not proof.

## Choose the Test Boundary

| Boundary | Use when |
|---|---|
| Unit | pure rules, transformations, calculations, state transitions |
| Component | behavior spans collaborating units inside one owned boundary |
| Integration | database, filesystem, queue, network adapter, framework, or module contract matters |
| Contract | producer/consumer API, event, schema, serialization, or compatibility changes |
| End-to-end | a small number of critical journeys need whole-system confidence |

Use the cheapest boundary that contains the failure mechanism. Do not replace a needed integration test with an isolated substitute, or local logic tests with slow end-to-end tests.

## Choose the Design Method

| Risk shape | Preferred method | Selection rule |
|---|---|---|
| input domains | equivalence partitioning | choose representatives with the same expected behavior |
| thresholds and ranges | boundary-value analysis | test below, at, and above meaningful boundaries |
| interacting business conditions | decision tables | cover distinct outcomes and prohibited combinations |
| large configuration combinations | pairwise or constrained combinatorial | use when exhaustive cases are impractical |
| lifecycle or workflow | state-transition testing | cover valid transitions, rejected transitions, and recovery |
| broad invariant | property-based testing | use when a stable property is stronger than examples |
| parser or hostile input | fuzzing | detect crash, invariant violation, leak, or unsafe acceptance |
| refactor or migration | differential testing | compare old/new results where equivalence is required |
| legacy behavior | characterization testing | pin observed behavior before changing structure |
| remote or partial failure | fault injection | exercise timeout, retry, interruption, duplicate, and recovery |
| concurrency | invariant, schedule, and stress testing | target races, ordering, atomicity, and idempotency |
| weak test oracle | mutation testing | prove assertions detect plausible defects |
| latency or throughput regression | controlled benchmark or performance regression | compare representative baseline and candidate measurements |
| peak traffic or capacity | load, stress, or capacity testing | locate limits and verify service-level behavior |
| resource retention or leak | soak testing and resource instrumentation | observe memory, handles, connections, disk, or queue growth |
| roles, tenants, or permissions | authorization matrix | cover allowed and denied actor-resource-action combinations |
| abuse, rate limits, or hostile workflows | adversarial and misuse-case testing | verify rejection, throttling, isolation, and bounded cost |
| sensitive data exposure | log, error, fixture, snapshot, and response inspection | prove secrets and personal data do not escape |
| dependency or runtime upgrade | compatibility, contract, and owned-boundary integration | exercise changed defaults and supported environments |
| critical user outcome | end-to-end scenario | keep few, stable, and behavior-focused |

Do not apply every method. Select a method only when its failure model exists in the impact table.

## Use Test Doubles Safely

Do not mock away the failure mechanism or observable contract.
Use test doubles only at stable substitutable boundaries.

A stable boundary may be internal or external. Preserve real integration semantics whenever serialization, transactions, framework behavior, concurrency, or protocol compatibility is part of the risk.

## Apply TDD Deliberately

Use `RED -> GREEN -> REFACTOR -> TRIANGULATE` when the contract is stable and direct RED execution is available. For non-reproducible or environment-specific defects, use the Baseline Gate alternatives and retain the missing observation as residual uncertainty.

Prefer characterization or differential evidence before behavior-preserving refactors. For deletions, test consumer migration and intended absence, compatibility, or rejection. Treat exploratory spike code as unverified until the mandatory Gates are satisfied.

## Design Cases Efficiently

- Cover relevant success, edge, error, recovery, performance, and abuse outcomes.
- Test invalid input only when rejection belongs to the contract.
- Prefer one clear behavioral reason for each test failure.
- Avoid giant snapshots, overspecified interaction checks, sleeps, retries, and order dependence.
- Control clocks, randomness, network, shared state, concurrency, and test load.
- Keep fixtures minimal and free of secrets or sensitive personal data.

## Assess the Oracle

Ask whether reintroducing the plausible defect would fail the test. Strengthen an oracle that merely executes a line, checks a substitute interaction unrelated to behavior, or accepts multiple incorrect outcomes.

For high-risk logic, use mutation, fault injection, differential, performance, or security testing when supported and proportionate. Treat surviving relevant mutants or unexplained regressions as evidence gaps, not as demands for universal scores.
