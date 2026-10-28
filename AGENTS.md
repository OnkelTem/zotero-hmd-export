# Project instructions

Read `README.md`, `docs/output-format.md`, `docs/zotero-bbt.md`,
`docs/output.md`, `docs/features/README.md`, `docs/backlog.md`, and the ADRs
before changing behavior.

## Skills

- `py-manager` for layout, packaging, tests, and tooling.
- `docs-manager` for README, AGENTS, and ADR prose.
- `feature-manager` for feature specs, backlog, and ADRs when the `agents/`
  submodule is initialized.
- This project replaces `py-manager`'s per-task files with feature specs and a
  backlog (ADR 011). Do not create per-task files.

## Project constraints

- Python 3.12+, standard library only.
- Distribution `zotero-hmd-export`; package `zotero_hmd_export`; CLI
  `zotero-hmd-export`.
- Zotero data comes only from Better BibTeX JSON-RPC at `127.0.0.1:23119`;
  never read `zotero.sqlite`.
- Built-in defaults < project config. The project config is the only user
  config; there is no global config. Commands write values to the project and
  books files, and `init` writes a complete self-documenting config.
- A project is a directory with `zotero-hmd-export.toml`; books live in the
  file named by `[project].books`, resolved relative to the config.
- `output_dir` is the final pages directory: never append `pages`, infer a
  graph root, or use an application API.
- Filename precedence: book `file_name`, project `file_name`, then built-in
  `{title}.md`; overrides are complete. Placeholders are `{author}`, `{title}`,
  and `{citekey}`; full rules are in `docs/output.md`.
- `export` validates and renders every book before writing; any error aborts
  without partial writes. Default `on_existing = "overwrite"`; unchanged
  content is not rewritten.
- v1 excludes image, ink, and rectangle annotations and PDF outline parsing.
- Render Markdown in Python; do not use a template engine.

## Rendering invariants

Full specification: `docs/output-format.md`.

- `[tree]` sets nesting, `[format]` sets appearance; they are independent.
- Tree, format, collapse, background, source, and tags emit nothing until
  configured.
- Predicates combine type, color, and `#tag` conditions with AND. A tag rule
  beats a rule without a tag; then more conditions, the last matching tag, and
  later config order.
- Absolute levels stop at `level6`; `rankN` is relative to the last absolute
  level and has no depth cap.
- `collapsed:: true` only on collapsed blocks with a nested block or a
  non-empty comment.
- A `next_line` source is block content, not a child block.
- Empty text renders `null`; newlines become `<br>`; two spaces per level; no
  blank lines.

## Testing

Use synthetic fixtures in `tests/fixtures/` and temporary directories. Tests
must never touch a real Zotero library, a real output graph, or the network.
Fixture values are documented in `docs/zotero-bbt.md`.

## Agent tooling

Agent definitions and skills live in the private `agents/` submodule (init with
`git submodule update --init --recursive`). `.opencode` is a symlink to
`agents/.opencode`. Read `agents/AGENTS.md` before changing agent
configuration. The exporter builds and tests without the submodule.

## Commit policy

Commits after completing a feature or backlog item are allowed. Never commit
secrets, generated artifacts, or `.venv`.

## Abandoned approaches

Do not reintroduce approaches rejected in the ADRs without a new ADR.
