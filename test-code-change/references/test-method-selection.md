# Scientific Test Method Selection

Choose methods from the failure model and observable contract. Prefer the smallest portfolio that can falsify the important claims.

## Define a Valid Test

For each case, specify:

1. **Hypothesis:** observable behavior or invariant.
2. **Setup and controls:** state, fixtures, clock, randomness, dependencies.
3. **Stimulus:** input or action.
4. **Oracle:** exact value, state, side effect, error, timing bound, or signal.
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

Use the cheapest boundary that includes the failure mechanism. Do not replace a needed integration test with mocks, or local logic tests with slow end-to-end tests.

## Choose the Design Method

| Risk shape | Preferred method | Selection rule |
|---|---|---|
| input domains | equivalence partitioning | choose representatives with the same expected behavior |
| thresholds and ranges | boundary-value analysis | test below, at, and above meaningful boundaries |
| interacting business conditions | decision tables | cover distinct outcomes and prohibited combinations |
| large configuration combinations | pairwise or constrained combinatorial | use when interactions matter but exhaustive cases are impractical |
| lifecycle or workflow | state-transition testing | cover valid transitions, rejected transitions, and recovery |
| broad invariant over generated inputs | property-based testing | use when a stable property is stronger than examples |
| parser or hostile input | fuzzing | assert no crash, invariant violation, leak, or unsafe acceptance |
| refactor or migration | differential testing | compare old/new results where equivalence is required |
| legacy behavior | characterization testing | pin observed behavior before changing structure |
| remote or partial failure | fault injection | exercise timeout, retry, interruption, duplicate, and recovery |
| concurrency | invariant, schedule, and stress testing | target races, ordering, atomicity, and idempotency |
| weak test oracle | mutation testing | use selectively to prove assertions detect plausible defects |
| critical user outcome | end-to-end scenario | keep few, stable, and behavior-focused |

Do not apply every method. Select a method only when its failure model exists in the impact map.

## Apply TDD Deliberately

Use the micro-cycle:

1. Add one behavior to the test list.
2. Write the smallest test that expresses its public contract.
3. Observe RED for the intended reason.
4. Implement the smallest GREEN behavior.
5. REFACTOR while green.
6. TRIANGULATE with another case when the first permits a false implementation.

Apply these mode-specific rules:

- **Bug fix:** require observed red-to-green regression evidence.
- **Stable new behavior:** prefer test-first development.
- **Behavior-preserving refactor:** establish characterization or differential evidence first.
- **Deletion:** test consumer migration and intended absence, compatibility, or rejection.
- **Exploration:** allow a disposable spike while the contract is unknown; test the production implementation.

## Design Cases Efficiently

- Cover relevant success, edge, error, and recovery outcomes.
- Test invalid input only when rejection belongs to the contract.
- Prefer one clear behavioral reason for each test failure.
- Reuse setup through local helpers only when it improves intent without hiding important state.
- Avoid giant snapshots, overspecified interaction mocks, sleeps, retries, and order dependence.
- Control nondeterminism; treat flaky behavior as a defect.
- Keep fixtures minimal and free of secrets or sensitive personal data.

## Assess the Oracle

Ask whether reintroducing the plausible defect would fail the test. Strengthen the oracle when a test merely executes a line, asserts a mock call unrelated to behavior, or accepts multiple incorrect outcomes.

For high-risk logic, use mutation testing when available and affordable. Treat surviving relevant mutants as evidence of an assertion or case gap, not as a demand for a universal mutation score.

## Expand Regression by Evidence

Run tests in increasing scope:

1. the new or directly changed behavior
2. sibling behavior sharing the implementation or invariant
3. affected consumers and boundary suites
4. required static, type, lint, and build checks
5. the full suite when broad coupling, repository policy, or cost justifies it

Stop only when every material risk has evidence at a boundary capable of exposing it. Report anything not run.
