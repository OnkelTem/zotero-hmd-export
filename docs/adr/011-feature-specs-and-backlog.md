# ADR 011: Feature specs and a backlog instead of task files

Status: Accepted
Date: 2026-10-24

## Context

Task files record execution, not product intent. Once a task is done, its file
is moved to `.tasks/history/`, where it duplicates what git already records and
adds little that ADRs and documentation do not already explain.

ADR documents answer "why this design?" but deliberately do not describe
user-visible capabilities. Code and tests show how behavior is implemented, but
not what the tool is supposed to do for its user. That leaves a gap between
architecture decisions and implementation details.

## Decision

- Describe user-visible capabilities in `docs/features/` as user stories with
  status, acceptance criteria, and links to ADRs, specs, code, and tests.
- Keep completed feature specs as living documentation with status `done`.
- Track non-feature work (bugs, chores, refactors, documentation fixes) in
  `docs/backlog.md`. Remove an item when it is done; git records the change.
- Record decisions that involve alternatives or lasting consequences in ADRs.
- Remove `.tasks/` and stop using per-task files. Git history, feature statuses,
  and ADRs replace task history.
- Remove `docs/handoff.md`. Session state, decisions, test fixtures, and next
  steps live in features, backlog, ADRs, README, and `AGENTS.md`.
- This project overrides the `.tasks/` layout required by the `py-manager`
  standard.

## Consequences

- A session starts from `AGENTS.md`, `docs/features/`, `docs/backlog.md`, and
  the ADRs; there is no separate handoff file.
- A feature that follows an existing decision does not need a new ADR; applying
  the decision is enough.
- A non-feature change no longer needs a durable per-task document.
- Feature specs must be kept honest: update them when behavior changes rather
  than letting them become stale wish lists.
- The feature/backlog workflow is documented in the project-local
  `feature-manager` skill, distributed through the private agents submodule
  (ADR 018). Global agent skills remain generic.
