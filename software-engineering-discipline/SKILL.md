---
name: software-engineering-discipline
description: "Engineering discipline for coding agents on large, complex codebases. Apply when writing, refactoring, or reviewing non-trivial code in real systems — enforce architecture boundaries, SOLID/cohesion, contracts, testability, and bounded blast radius instead of just completing the task."
---

# Software Engineering Discipline

Constraints that force sound engineering on large, complex systems. The goal is not to *complete the task* — it is to leave the system **more coherent, not less**. Bias toward fitting the system over local cleverness. For genuinely trivial scripts, use judgment.

A passing test is necessary, not sufficient. Code that works but corrodes the architecture is a defect.

## 0. Understand Before You Touch

**You are editing someone's system, not a blank file.**

Before writing in an existing codebase:
- Read the module you're changing AND its callers/callees. Know the data flow in and out.
- Find the existing pattern for this kind of work (`grep`/search a sibling feature) and follow it. Consistency beats personal preference.
- Identify the architectural layer you're in (domain / application / infrastructure / UI) and its rules.
- Locate the existing tests; they encode intended behavior and contracts.

Test: Can you name the layer, the existing convention, and who depends on this code? If not, stop and investigate.

## 1. Respect Boundaries & Dependency Direction

**Coupling is the enemy. Dependencies point inward and downward, never sideways or up.**

- Honor module/package boundaries. Don't reach across a layer to grab internals — call the public interface.
- Dependencies flow toward stable abstractions (Dependency Inversion). High-level policy must not depend on low-level detail.
- No new circular dependencies. No domain logic importing framework/IO. No business rules in controllers/handlers.
- If the clean change requires crossing a boundary, that's a design signal — surface it, propose the seam, don't smuggle it through.

Test: Could you swap the database/HTTP/UI layer without touching core logic? If your change makes that harder, reconsider.

## 2. High Cohesion, Single Responsibility

**One module, one reason to change. Group what changes together; separate what changes for different reasons.**

- A function/class/module should do one coherent thing. If you need "and" to describe it, split it.
- Separate concerns: policy vs mechanism, what vs how, decision vs side-effect.
- Keep related logic together; don't scatter one responsibility across many files, nor pile unrelated responsibilities into one.
- Open/Closed: extend behavior by adding code, not by editing stable core paths with special-case `if`s.

Test: Does a single conceptual change touch one place, or shotgun across many? Shotgun = wrong seams.

## 3. Abstractions That Earn Their Keep

**Right abstraction reduces total complexity. Wrong abstraction adds indirection without removing it.**

- DRY is about knowledge, not text. Deduplicate a *decision/rule*; don't merge code that merely looks similar (premature DRY couples unrelated things).
- YAGNI: build for today's known requirements. No speculative generality, no "framework" for one caller, no config knobs nobody asked for.
- Prefer a clear name and a small function over a clever one-liner. Code is read far more than written.
- Rule of three: tolerate a little duplication until the real pattern is obvious, then extract.

Test: Does this abstraction let a reader understand *less* to change *more*? If it forces them to learn machinery first, it's wrong.

## 4. Design by Contract & Defensive Edges

**Define the contract; validate at the boundary; trust the core.**

- Make interfaces explicit: inputs, outputs, preconditions, postconditions, invariants, error modes. Sketch the contract before the implementation.
- Validate untrusted input at the system edge (API/UI/IO). Inside the trusted core, assume invariants hold — don't re-check everywhere.
- Fail fast and loud on programmer errors (assert invariants); handle expected operational errors deliberately. Don't swallow exceptions.
- Don't break a published contract silently. Changing a signature/behavior is an API change — find callers, version it, or migrate them.

Test: Can a caller use this from the signature + types + name alone, without reading the body?

## 5. Build It Testable, Observable, Evolvable

**Untestable code is a design defect, not a testing gap.**

- If something is hard to test, the design is too coupled — inject dependencies, isolate side-effects, separate pure logic from IO. Fix the design, not the test.
- Add the test that pins the behavior you're implementing or the bug you're fixing. For bugs: reproduce with a failing test first, then fix.
- Make state observable where it matters: meaningful logs/metrics at boundaries and failure paths — not noise everywhere.
- Leave seams for change. Hardcode less, name constants, keep config out of logic. Optimize for the next person's edit, not the cleverest current diff.

Test: Could a teammate test this in isolation and understand a production failure from the signals you left?

## 6. Bounded Blast Radius

**The size of the diff should match the size of the request. Touch only what the change requires.**

- Don't opportunistically refactor, reformat, or "improve" unrelated code in the same change. Note it separately.
- Keep concerns in separate changes: a refactor and a feature don't share one commit.
- Before a wide change, state a brief plan and the impact surface (what files/modules, what callers, what contracts move). Confirm if the radius is large.
- After changing a contract, follow every caller. Don't leave half-migrated state.

Test: Every changed line traces to the request. The reviewer can understand the diff without a map of the whole repo.

## Operating Loop (non-trivial changes)

```
1. Understand   → name the layer, the convention, the callers, the existing tests
2. Design       → state the contract + the seam + the blast radius; pick the simplest fit
3. (Confirm)    → if the radius is large or a boundary/contract must move, surface it first
4. Implement    → smallest change that fits the architecture; follow existing patterns
5. Verify       → tests pin new behavior; existing tests still green; diff is bounded
6. Review self  → run §1-6 tests; if any fails, fix the design, not just the symptom
```

---

**Working indicators:** changes fit existing patterns instead of inventing new ones; diffs stay scoped to the request; new code is testable without rework; boundaries and dependency direction stay intact; the reviewer can follow a contract from its signature; the system is more coherent after the change, not just more complete.