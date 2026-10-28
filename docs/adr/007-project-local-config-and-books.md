# ADR 007: Project-local layered config and multi-book export

Status: Superseded in part by ADR 009 and ADR 010
Date: 2026-10-23

## Context

The user maintains many separate note graphs and projects. A single global target
directory and a per-run Zotero picker are poor fits: the target and the books
belong to one project. The user also wants each book added once, with all project
books processed on each run. The earlier shared global defaults were later
removed by ADR 010.

## Decision

- A project is a directory containing `zotero-hmd-export.toml`.
- The project config owns `output_dir`, `books`, `file_name`, and render/output
  overrides.
- `books` is a path relative to the project config; it points to a separate
  `books.toml` with `[[books]]` entries.
- A project config provides all defaults (ADR 010). There is no global user
  config.
- `init` creates the project config and an empty books file.
- `add` stores a book once; `--update` refreshes stored metadata.
- `export` processes all books (or one with `--book`).
- All books are validated and rendered before any file is written. Any validation,
  fetch, or render error aborts the export without partial writes.

## Consequences

- Each project can target a different output directory and namespace template.
- Books are a stable project artifact, not an interactive choice on every run.
- A broken book blocks the whole export; fixing it and rerunning is deterministic.
- Each project config is complete; there is no global user config (ADR 010).
