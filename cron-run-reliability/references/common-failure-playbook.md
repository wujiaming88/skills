# Common failure playbook

Use this playbook only after the applicability gate in `SKILL.md` passes. These patterns are generic to long isolated Cron runs; task-specific paths, artifact names, validators, repositories, commands, and URLs remain in the business prompt.

## Response model

For every incident, separate five questions:

1. **Symptom** — what appeared to fail?
2. **Durable evidence** — what current-run artifacts or externally verified states exist?
3. **Criticality** — is the failed boundary required, optional, or only diagnostic?
4. **Recovery** — what is the first unverified boundary?
5. **Terminal class** — `SUCCESS`, `SUCCESS_WITH_WARNINGS`, or `BLOCKED`?

Never let the most recent error automatically become the final result.

## Child status abnormal but artifacts exist

Symptoms include failed/unknown child status, missing completion event, non-deliverable terminal turn, or a child that stopped after a tool result.

1. Do not immediately respawn the child.
2. Check exact current-run artifacts and completion markers with `check-files`.
3. Run the existing semantic validators.
4. If required artifacts and semantics pass, continue from the next boundary and record a warning.
5. If the child reports success but required artifacts are absent, classify `BLOCKED`.

Session state is supporting evidence; durable current-run artifacts are authoritative for handoff completion.

## `WAIT_TIMEOUT`

`WAIT_TIMEOUT` is a checkpoint, not a fatal result.

1. Re-run `check-files` immediately.
2. Inspect partial current-run artifacts and whether the child is still active.
3. If the overall run budget permits, perform another bounded wait.
4. When the run budget is exhausted, classify `BLOCKED` only if required evidence is still missing.

Never use an infinite loop, unbounded sleep, or active process kill to end normal waiting.

## Asynchronous completion event missing

Do not make a long isolated run depend exclusively on an asynchronous completion event. Require child tasks to persist artifacts and write their completion marker last. Recover through the run directory if event delivery is absent.

## Polling or control process fails

A failed control process does not automatically invalidate completed business work.

1. Do not kill a healthy polling process merely because a child session looks abnormal.
2. Prefer waits that end naturally and emit structured status.
3. After interruption, re-check current-run artifacts and downstream boundaries.
4. Preserve independently verified success; classify the control failure as a warning unless it left a required boundary unverified.

## Expected path does not match actual path

1. Read the current run's artifact manifest or handoff contract.
2. Do not guess paths or perform broad historical scans as the primary recovery mechanism.
3. Correct the contract or locate the current-run output before repeating business work.
4. Treat an unexpected path as `BLOCKED` when ownership or current-run provenance cannot be established.

## Stale artifact or completion marker

1. Accept evidence only from the unique current run directory.
2. Keep each run directory initially empty.
3. Write artifact bodies atomically and completion markers last.
4. On recovery, continue using the original run identity; do not mix evidence from separate attempts.

## Noncritical diagnostic failure

Examples include optional history inspection, auxiliary grep, cleanup reporting, or a secondary status query.

- Required artifact, semantic, build, Git, or HTTP boundary failure: `BLOCKED` when applicable.
- Auxiliary diagnostic failure: `WARNING`.
- Child status abnormal with valid artifacts: `WARNING`.
- Delivery failure after verified publication: `WARNING`.

A diagnostic command must not create a new fatal condition unless its result is itself an explicitly required boundary.

## Git state uncertain

1. Do not infer success from push prose or a cached tracking ref.
2. Use `check-git --verify-remote` when live remote synchronization is required.
3. If local and live remote heads already match, do not commit or push again.
4. If the repository changes during verification, fail conservatively and retry verification after it becomes quiescent.
5. Escalate rather than auto-rewriting history when branches diverge.

## HTTP temporarily unavailable

1. Use finite retries with request and total deadlines.
2. Do not republish merely because the first request is non-2xx.
3. If HTTP availability is required, exhausted retries mean `BLOCKED` even when Git passed.
4. If HTTP is optional, report `WARNING` or `N/A` according to the task contract.
5. Preserve query and credential secrecy in evidence output.

## Interrupted run or host restart

1. Reopen the original current-run directory.
2. Revalidate existing artifacts and all already-reached external boundaries.
3. Resume from the first unverified required boundary.
4. Do not regenerate, recommit, repush, or republish evidence that already validates.
5. If current-run ownership cannot be established, stop as `BLOCKED` rather than mixing runs.

## Tool degradation

When a nonessential tool is unavailable, use an already approved alternative verification path if one exists. Record the degradation as a warning. Do not silently weaken a required acceptance criterion.

## Boundary table

| Evidence boundary | Required result when applicable | Failure class |
|---|---|---|
| Current-run handoff files | exact expected regular files present | `BLOCKED` |
| Business semantics | existing task validator passes | `BLOCKED` |
| Build | existing build command passes | `BLOCKED` |
| Git publication | expected branch clean and synced to live remote | `BLOCKED` |
| HTTP publication | required public URL returns 2xx within budget | `BLOCKED` |
| Child/session status | supports but does not override artifacts | `WARNING` when artifacts validate |
| Auxiliary diagnostics | optional evidence only | `WARNING` |
| Delivery/notification | does not erase verified publication | `WARNING` unless contract says required |

## Keep business logic out

Do not add task names, report cadence, repository names, date paths, content coverage thresholds, editorial rules, build commands, agent assignments, or publication URLs here. Put those in the task prompt or validator. Add a new failure pattern only when it is reusable across multiple long isolated Cron jobs and can be expressed without business-specific constants.
