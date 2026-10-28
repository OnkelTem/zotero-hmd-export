# 006 — Export diagnostics

Status: done

## User story

As a researcher, I want to check my project and Zotero setup before exporting,
so that configuration problems surface with a clear error instead of a partial
export.

## Acceptance criteria

- [x] `doctor` reports the project config path.
- [x] `doctor` checks the output directory and books file.
- [x] `doctor` checks filename placeholders against stored book metadata.
- [x] `doctor` checks the Better BibTeX connection.
- [x] Failures produce actionable messages and a non-zero exit code.

## Out of scope

- Repairing configuration automatically.
- Checking a specific book without exporting it.

## References

- User docs: `README.md` (Commands, Troubleshooting)
- Code: `zotero_hmd_export/cli.py`, `zotero_hmd_export/config.py`,
  `zotero_hmd_export/zotero.py`
- Tests: `tests/test_cli.py`
