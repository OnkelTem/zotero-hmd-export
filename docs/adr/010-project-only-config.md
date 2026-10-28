# ADR 010: Project-only configuration

Status: Amended in part by ADR 012
Date: 2026-10-24

## Context

The global config added a second user-facing file and made it unclear where a
setting should be edited. The project config was also minimal and did not show
the available rendering rules. The user wants one complete, self-documenting
config per project.

## Decision

- Remove the global user config entirely.
- `zotero-hmd-export.toml` is the only user config.
- `init` writes a complete config with `[project]`, `[zotero]`, `[tree]`, and
  `[format]`, including English instructions and examples.
- Remove `[defaults]`; `file_name`, `include_properties`, and `on_existing` live
  in `[project]`.
- `load_config` reads only the project config. Missing `[zotero]`, `[tree]`, or
  `[format]` sections fall back to built-in defaults, so minimal and older
  project configs still load.
- `file_name` precedence is book override, project, then the built-in
  `{title}.md`.
- There is no separate command to refresh or migrate a config. `init --force`
  rewrites a project config. Existing global configs are ignored.
- The packaged template remains only as the body used by `init`; it is not
  copied to a user config directory.

## Consequences

- Each project is self-contained and fully explains its own settings.
- Changing built-in defaults in a new version does not rewrite existing project
  configs.
- Users with an old global config must move any custom rules into the project
  config manually if they want them.
- This supersedes the global-config parts of ADR 007 and ADR 009.

## Amendment (2026-10-24)

ADR 012 removed the built-in tree and format defaults. A missing `[tree]` or
`[format]` section now means no rules. The default BBT port and the scalar
`[project]` defaults remain.
