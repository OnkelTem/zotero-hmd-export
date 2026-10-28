# 001 — Project setup

Status: done

## User story

As a researcher, I want to initialize a project with an output directory and a
books file, so that repeated exports use the same configuration.

## Acceptance criteria

- [x] `init` creates `zotero-hmd-export.toml` and the books file.
- [x] `init` requires an existing output directory.
- [x] Relative output and books paths are resolved against the project config.
- [x] The generated config is complete and self-documenting; required values are
      filled in and optional rules are shown as commented examples.
- [x] A missing `[zotero]` section uses the default BBT port.
- [x] Missing `[tree]` or `[format]` sections mean no tree or format rules.
- [x] A missing `[logseq.collapse]` section means no collapse rules and a false
      default.
- [x] A missing `[logseq.background]` section means no background colors.
- [x] A missing `[source]` or `[tags]` section means no source or tag output.
- [x] There is no global user config and no separate config-refresh command.

## Out of scope

- Migrating an existing global config.
- Creating the output directory automatically.

## References

- ADRs: `docs/adr/007-project-local-config-and-books.md`,
  `docs/adr/010-project-only-config.md`,
  `docs/adr/012-no-implicit-tree-format-defaults.md`,
  `docs/adr/014-collapsed-blocks.md`,
  `docs/adr/015-configurable-source-metadata.md`,
  `docs/adr/016-tag-output-filtering.md`,
  `docs/adr/017-background-colors.md`
- User docs: `README.md` (Project config)
- Code: `zotero_hmd_export/config.py`, `zotero_hmd_export/cli.py`
- Tests: `tests/test_config.py`, `tests/test_cli.py`
