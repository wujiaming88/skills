# Design boundary

The skill exists only to remove error-prone, model-generated control scripts from long isolated Cron runs.

Included:

- bounded waiting for child/file handoffs;
- strict point-in-time checks of opened absolute regular files and glob matches;
- trusted-repository clean/synced Git verification on the explicitly checked-out target branch, optionally against its live remote branch;
- bounded public HTTP(S) 2xx verification, including public-address checks before requests and after every redirect;
- evidence-first terminal classification and idempotent recovery guidance.

Explicitly excluded:

- reminders, one-command jobs, normal backups, health checks, and simple fetch-and-send tasks;
- scheduling or Cron creation/editing;
- persistent workflow state, DAGs, business retries, or orchestration engines;
- research, editorial, factual, or domain-specific quality rules;
- arbitrary command execution wrappers;
- content generation, builds, commits, pushes, publication, or notification delivery;
- date-specific paths, repository names, URLs, or business logic.

Filesystem results describe the inode metadata observed while each file was safely open; paths can change immediately afterward and are not durable ownership or current-run proof. The helper observes mechanical evidence only. Business prompts own semantics and established build/publish commands. Additions require a reusable mechanical need, multiple long-job use cases, and regression tests.
