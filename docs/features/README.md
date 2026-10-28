# Features

User-visible capabilities of `zotero-hmd-export`. Each feature is a living
specification: update it when behavior changes instead of adding a new version
on top.

## Statuses

- `planned` — accepted for future work, not implemented.
- `active` — implementation is in progress.
- `done` — implemented and covered by tests.

Non-feature work (bugs, chores, refactors, documentation fixes) lives in
`docs/backlog.md`. Decisions with alternatives or lasting consequences are
recorded in `docs/adr/`.

## Index

| ID | Feature | Status |
|---|---|---|
| [001](001-project-setup.md) | Project setup | done |
| [002](002-book-catalog.md) | Book catalog | done |
| [003](003-annotation-export.md) | Annotation export | done |
| [004](004-filename-templates.md) | Filename templates | done |
| [005](005-tree-and-format-rules.md) | Tree and format rules | done |
| [006](006-export-diagnostics.md) | Export diagnostics | done |
| [007](007-relative-tree-levels.md) | Relative tree levels | done |
| [008](008-collapsed-blocks.md) | Collapsed Logseq blocks | done |
| [009](009-configurable-source-metadata.md) | Configurable source metadata | done |
| [010](010-tag-output-filtering.md) | Tag output filtering | done |
| [011](011-background-colors.md) | Background colors by annotation or level | done |

## File format

Each feature file contains:

- status;
- a user story;
- acceptance criteria;
- out-of-scope items;
- links to ADRs, specifications, code, and tests.

Feature files describe intent and behavior, not implementation steps. Execution
plans belong to the session; non-feature work belongs to the backlog.
