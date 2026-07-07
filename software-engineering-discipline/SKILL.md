---
name: software-engineering-discipline
description: "Engineering discipline for AI coding agents. Apply when writing, refactoring, or reviewing code that will be maintained. Not a tutorial on SOLID/DRY (you already know those) — it calibrates the trade-off calls and hard limits where agents predictably go wrong, and forces you to verify instead of guess."
---

# Software Engineering Discipline

You already know SOLID, DRY, YAGNI, design-by-contract, Clean Architecture. This skill does **not** re-teach them. It fixes the two things you actually get wrong: **making the wrong trade-off call** (over-abstracting, over-engineering, guessing) and **crossing a hard limit** (data loss, silent contract breaks, calling things that don't exist).

**Prime directive:** Leave the codebase more coherent than you found it, and write code a top engineer would sign off on — clear, cohesive, correctly scoped. A passing test is necessary, not sufficient: code that works but corrodes the design is a defect.

**Apply to:** any code that will be read or maintained again.
**Relax (not the RED LINES) for:** genuine throwaway — a scratch script, a spike you will delete, a one-off you won't commit. Size is not the test; *"will anyone maintain this?"* is.

---

## RED LINES (never cross, regardless of how small the change is)

Do not size-gate these. A 5-line migration or 10-line auth change is exactly where these bite.

1. **Verify before you use it.** Every API, method, import, flag, config key, constant — confirm it exists before calling it (read the source / grep the symbol / check the installed version, not your memory). If you could not verify, write `[UNVERIFIED]` next to it. Never present a guess as fact.
2. **Never break a published contract silently.** A signature/behavior/wire-format/schema change is an API change: find the callers, migrate or version them.
3. **Migrations are expand → migrate → contract.** Never drop/rename a column (or remove a field) in the same release as the code that stops using it. Reads stay backward-compatible.
4. **Never weaken or delete a test to make it pass.** If a test fails, fix the code or fix the test's *correctness* — never gut the assertion.
5. **Never swallow an error into a silent default.** No `except: return None` / empty `catch {}`. Handle it, or let it propagate with context.
6. **Secrets/PII never touch code or logs.** Read from the existing secret/config mechanism; never hardcode (incl. tests/fixtures), never commit `.env`, redact in errors.
7. **Authorize at the boundary — not just validate shape.** Parameterize queries; treat all external input as hostile.
8. **Every remote call has a timeout and a defined failure behavior** (retry-with-backoff / fallback / fail-closed). Retried or at-least-once operations need an idempotency key.
9. **Scope is bounded.** Every changed line must trace to the request. Necessary scope (a wide rename, a required migration) is fine; unrelated "improvements" are not. A refactor and a feature never share one commit.

---

## TRADE-OFF CALLS (where your defaults are wrong — bias as stated)

You default to *too much structure*. These pull you back. When unsure, pick the simpler option.

- **Abstraction:** Introduce an interface/base class **only when ≥2 real implementations exist now, or a test seam genuinely needs it.** One implementation → concrete class. Building a "framework" for one caller is the defect, not good design.
- **Branch vs. polymorphism:** A plain `if` is usually correct. Reach for a strategy/subclass **only** when variants form a stable, growing set added by different owners. Unsure → `if`.
- **DRY:** Deduplicate the *same knowledge/decision*, not code that merely *looks alike*. Two functions with similar shape but different reasons to change → leave them. Wait for the third occurrence before extracting coincidental similarity.
- **Cohesion:** A unit does one thing. If its name needs an "and", split it. Don't smear one responsibility across files, or pile unrelated ones into one class.
- **Naming > cleverness:** A clear name + a plain function beats a clever one-liner. Code is read far more than written.
- **Follow the local convention** even if you'd personally do it differently. Match the sibling code's style, error handling, and layering before importing your own taste.
- **Boundaries:** Call the public interface, don't reach into a layer's internals. Core/domain logic must not import IO/framework/UI. If a clean change needs to cross a boundary, say so — don't smuggle it.

---

## BEFORE YOU WRITE (for any non-trivial change)

State these first. If you can't, you don't understand the change yet — go read.

- **Understand:** read the module you're touching AND its callers/callees; trace data in/out; read the existing tests (they encode the contract); find the sibling pattern and follow it.
- **Contract:** for the unit you're adding/changing, state inputs · outputs · preconditions · postconditions · error modes. Validate untrusted input at the edge; assert impossible-to-violate invariants in the core (don't sprinkle asserts everywhere).
- **Blast radius:** files/callers touched · contracts or wire-formats that move · migrations/flags introduced · how to roll back. If the radius is large or a boundary/contract/migration moves, surface it before implementing.

## TESTING (don't stop at the happy path)

- Pin the new behavior with a test; for a bug, reproduce it with a failing test *first*, then fix.
- Test the **edges and the error modes you declared in the contract**, not just the success case.
- Test **behavior, not implementation** — no mock-heavy tests that stay green while the behavior breaks.
- Tests must be deterministic: no reliance on real clock, random, network, or ordering.
- Hard to test = too coupled. Fix the design (inject deps, isolate IO, separate pure logic), not the test.

## DEPENDENCIES & OBSERVABILITY

- **Don't add a dependency for something trivial.** Prefer stdlib/existing deps; check the manifest before importing; don't pull a package (and its tree) to solve a one-liner; watch for typosquat-adjacent names.
- Emit signals at **boundaries, state transitions, and failure paths** — structured, with correlation/request IDs. Not inside hot loops, not on the happy path of pure functions.

---

## DELIVERY GATE — must pass before you report "done"

Output this checklist filled in. A failed item means you are **not done** — fix it, don't report success.

```
□ Contract declared and matches the implementation
□ New behavior + declared error modes covered by tests
□ Tests actually run — output/summary attached (not "should pass")
□ No API/import/config/constant used unverified (or marked [UNVERIFIED])
□ No RED LINE crossed
□ Blast radius stated; every changed line traces to the request
□ Handoff note: what changed · why · what you verified · risks · what you deliberately did NOT do
```

**Loop:** Understand → Contract + Blast radius → (confirm if large) → Implement (simplest fit, follow local convention) → Test edges & errors → Delivery gate.
