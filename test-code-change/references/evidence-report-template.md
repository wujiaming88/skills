# Change Test Evidence

Use this template for substantial implementation or review work. Omit empty sections and keep the user-facing summary concise.

## Change Basis

- **Mode:** implementation / review / blocked
- **Request and acceptance criteria:**
- **Comparison base and inspected diff:**
- **Repository instructions and commands discovered:**
- **Pre-existing failures or unrelated changes:**

## Observable Contracts

| ID | Changed behavior | Inputs and preconditions | Outputs, state, and side effects | Error modes |
|---|---|---|---|---|

## Impact and Risk

| Risk ID | Failure mode and evidence | Affected surface | Inherent level | Required response |
|---|---|---|---|---|

Record unknown callers, environments, contracts, and assumptions as explicit risks.

## Test Design

| Risk ID | Boundary | Method | Cases | Oracle | Expected evidence |
|---|---|---|---|---|---|

Explain why omitted test types do not fit the identified failure modes. Do not list every possible method.

## TDD or Baseline Trace

- **RED or characterization evidence:**
- **GREEN evidence:**
- **Refactor or triangulation evidence:**

Use `N/A` with a reason when test-first development does not fit the change.

## Executed Evidence

| Scope | Exact command | Result | What it proves |
|---|---|---|---|
| Targeted |  |  |  |
| Affected suite |  |  |  |
| Integration or contract |  |  |  |
| Type, lint, build, static |  |  |  |
| Full suite |  |  |  |

Never place an unexecuted recommendation in this table as a passing result.

## Coverage and Oracle Quality

- **Repository gate:**
- **Changed executable lines and branches:**
- **Material uncovered changes and rationale:**
- **Mutation, differential, property, or fault evidence:**
- **Oracle quality concerns:**

## Failure Handling and Observability

- **Errors and partial failure:**
- **Timeout, retry, idempotency, concurrency, and cleanup:**
- **Logs, metrics, traces, and sensitive-data checks:**

Use `Not impacted` only after checking the impact map.

## Residual Risk

| Risk ID | Executed controls | Residual level | Remaining uncertainty or follow-up |
|---|---|---|---|

## Handoff

Summarize:

1. what behavior changed
2. which tests and checks actually ran
3. what the evidence covers
4. what was not run and why
5. the remaining risk

Bound the conclusion to the discovered impact map and executed environment. Do not claim absolute completeness.
