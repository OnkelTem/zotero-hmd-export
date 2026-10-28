# 004 — Filename templates

Status: done

## User story

As a researcher, I want page filenames to follow my graph's naming convention,
so that exported pages fit alongside manually created notes.

## Acceptance criteria

- [x] `file_name` precedence is book override, then project value, then the
      built-in `{title}.md`.
- [x] Allowed placeholders are `{author}`, `{title}`, and `{citekey}`.
- [x] A used placeholder with an empty value aborts the export.
- [x] An unused placeholder with an empty value is ignored.
- [x] Unknown placeholders, format specifiers, and conversions are errors.
- [x] A literal `/` in the final filename is rejected.
- [x] Literal `___` is preserved; `/` is not converted to `___`.
- [x] In substituted values, `/` becomes `-` and `: ? " * < > | \ # %` are
      percent-encoded.
- [x] Literal template text is not re-encoded.
- [x] `.md` is appended when missing.

## Out of scope

- Auto-detecting a graph naming convention.
- Renaming or deleting pages that are no longer produced.

## References

- ADRs: `docs/adr/008-filename-templates.md`,
  `docs/adr/010-project-only-config.md`
- User docs: `README.md` (Filename rules)
- Code: `zotero_hmd_export/writer.py`, `zotero_hmd_export/cli.py`
- Tests: `tests/test_writer.py`, `tests/test_cli.py`
