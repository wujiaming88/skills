---
name: "cron-run-reliability"
description: "提升长时 isolated Cron 的可靠性：有界等待、机械验收、故障恢复与证据化收口"
---

# Cron Run Reliability

Use only for long OpenClaw `isolated` Cron jobs with child-agent/file handoffs, multiple durable artifacts, or a multi-step publication boundary.

## Applicability gate

Use this skill only when at least one is true:

- an isolated Cron spawns child agents and must wait for file handoffs;
- a run has multiple durable artifacts plus a release/publication boundary;
- a comparable run previously suffered false success, false failure, or unsafe model-generated polling code.

Do **not** use it for reminders, one-command jobs, ordinary backups, simple health checks, fetch-and-send jobs, or short tasks with no child/file handoff. Those jobs must stay simple.

This is a narrow execution-reliability layer. It does not schedule or edit Cron jobs, define research/editorial quality, create workflow state, retry business work, run arbitrary business commands, build, commit, push, publish, or deliver notifications.

## Fixed helper only

Use the bundled, regression-tested helper:

```bash
python3 scripts/reliable_cron.py --help
```

Do not synthesize ad-hoc polling loops, wrapper scripts, or shell process-kill logic at runtime.

## Run contract

1. Create a unique, initially empty, absolute run directory for each invocation.
2. Put only current-run artifacts in it. Write artifact bodies to temporary names, atomically rename them into place, and write completion markers last.
3. Start each child task once. A child that writes its files must also return a short final assistant message; do not stop on a tool result.
4. Wait only with the bundled `wait` command. `WAIT_TIMEOUT` is a checkpoint, not a task failure.
5. After every wait, run `check-files`. File checks prove only point-in-time metadata for the inode opened during inspection. They do not prove semantic correctness, provenance, expected glob cardinality, or later path stability.
6. Apply existing business validators separately. A completion marker is not a substitute for semantic validation.
7. Run existing build, commit, push, or publish commands directly when the business task requires them. This skill does not generate or execute those commands.
8. Run `check-git` and `check-http` only when a repository or public URL is actually part of the task.
9. Classify the final result as `SUCCESS`, `SUCCESS_WITH_WARNINGS`, or `BLOCKED` from durable evidence. Notification failure must not overwrite verified publication success.
10. Before retrying work, inspect current-run evidence first to avoid duplicate work or publication.

## Recovery order

When a run appears stalled or failed, do not improvise a recovery script. Follow this order:

1. Identify the current unique run directory and expected artifact manifest.
2. Inspect current-run completion markers and artifacts with `check-files`.
3. Run the task's existing semantic validators separately.
4. Check whether the child is still active only as supporting evidence; session status is not authoritative.
5. Verify applicable build, Git, HTTP, and delivery boundaries independently.
6. Resume from the first unverified boundary; do not repeat already verified work.
7. Classify the terminal result from evidence, not from the last tool error.

For symptom-specific handling, read `references/common-failure-playbook.md`. It is a generic incident playbook, not a business workflow.

## Commands

### `wait`

```bash
python3 scripts/reliable_cron.py wait \
  --file /absolute/run/completed.marker \
  --glob '/absolute/run/part-*.data' \
  --timeout 1800 \
  --interval 30 \
  --min-bytes 1
```

- All exact files must exist, be regular non-symlink files, and meet `--min-bytes`.
- Every matched glob item must also pass; an empty glob is not success.
- For an exact expected set, enumerate every item with `--file`; a glob cannot prove count.
- Timeout emits one JSON line with `status: "WAIT_TIMEOUT"` and exits `0` so the Cron turn can inspect evidence naturally.

### `check-files`

```bash
python3 scripts/reliable_cron.py check-files \
  --file /absolute/run/completed.marker \
  --file /absolute/run/final-artifact.data \
  --min-bytes 1
```

Missing, empty, non-regular, or symlinked paths fail mechanically. This command does not validate meaning.

### `check-git`

```bash
python3 scripts/reliable_cron.py check-git \
  --repo /absolute/repository \
  --remote origin \
  --branch main \
  --verify-remote \
  --command-timeout 30
```

- The named branch must be checked out; detached HEAD or another branch fails.
- Requires a clean worktree, no merge/rebase/cherry-pick/revert/bisect state, and local `HEAD` equal to the selected remote branch.
- `--verify-remote` uses `git ls-remote` rather than trusting a cached tracking ref.
- Before/after snapshots must agree; observed concurrent repository change fails conservatively.
- Each Git command runs in a process group. Timeout or interruption sends TERM then KILL and emits redacted evidence.

### `check-http`

```bash
python3 scripts/reliable_cron.py check-http \
  --url https://example.com/published-resource \
  --attempts 5 \
  --interval 10 \
  --request-timeout 20 \
  --total-timeout 120
```

- Only credential-free public HTTP(S) destinations are allowed. Any non-global DNS answer fails.
- Every redirect and final URL are revalidated; validated DNS answers are pinned against rebinding.
- Query strings and fragments are omitted from output; exception text is normalized and redacted.
- Request and total deadlines include bounded worker lifecycle accounting. Fixed cleanup grace may slightly exceed the requested deadline and fails conservatively.

## Exit and output contract

Every invocation writes exactly one JSON object to stdout.

- validated success: exit `0`, `ok: true`;
- `WAIT_TIMEOUT`: exit `0`, `ok: false`, because it is a nonfatal checkpoint;
- invalid arguments, failed mechanical checks, or checker-internal failures: exit `2`, `ok: false`;
- SIGINT or SIGTERM: clean active Git/HTTP workers, emit `status: "INTERRUPTED"`, and exit `130`.

Do not use stderr parsing or prose matching as task evidence.

## Final evidence report

Report only applicable rows; use `N/A` rather than inventing passes:

```text
Run directory: /absolute/run/unique-id
Child/file handoff: PASS | WARNING | BLOCKED | N/A
Mechanical files: PASS | BLOCKED | N/A
Business validators: PASS | BLOCKED | N/A
Build: PASS | BLOCKED | N/A
Git publication: PASS | BLOCKED | N/A
HTTP publication: PASS | BLOCKED | N/A
Delivery: PASS | WARNING | N/A
Final: SUCCESS | SUCCESS_WITH_WARNINGS | BLOCKED
```

## Evidence precedence

- Valid current-run files outweigh an unreliable child-session status.
- A child marked successful without required files is `BLOCKED`.
- A child marked failed after producing all validated current-run artifacts is normally a warning.
- Mechanical checks never override semantic validators.
- Old artifacts outside the unique run directory are not evidence for the current run.
- A late noncritical diagnostic or delivery failure must not erase independently verified success.
