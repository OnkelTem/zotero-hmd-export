# 003 — Annotation export

Status: done

## User story

As a researcher, I want my PDF highlights, underlines, comments, tags, and page
links exported as a nested Markdown page, so that the result is usable in a
Logseq-style graph without manual cleanup.

## Acceptance criteria

- [x] `export` processes every book in the catalog, or one book with `--book`.
- [x] `--dry-run` renders pages without writing files.
- [x] Annotations are sorted by the Zotero annotation sort index.
- [x] Each annotation becomes a list item at the resolved nesting level.
- [x] Comments become nested list items wrapped in `==...==`.
- [x] Tags appear inline as `#[[tag]]` before source metadata when enabled by
      `[tags]`.
- [x] Source metadata is controlled by `[source]` and can be inline, on a
      continuation line, or disabled.
- [x] Block backgrounds are controlled by `[logseq.background]`.
- [x] Empty annotation text renders the literal `null`.
- [x] Newlines inside text and comments become `<br>`; no blank lines are
      emitted.
- [x] Image and ink annotations are skipped.
- [x] Every book is validated and rendered before any page is written.
- [x] Content-equal pages are not rewritten; changed pages are written
      atomically.
- [x] `on_existing = "error"` aborts on an existing different page.

## Out of scope

- Image, ink, and rectangle annotations.
- PDF outline parsing.
- Merging manual edits into an existing page.

## References

- ADRs: `docs/adr/002-write-logseq-md-directly.md`,
  `docs/adr/003-render-markdown-in-python.md`,
  `docs/adr/005-overwrite-logseq-page.md`,
  `docs/adr/009-tree-and-format-rules.md`,
  `docs/adr/013-relative-tree-levels.md`,
  `docs/adr/014-collapsed-blocks.md`,
  `docs/adr/015-configurable-source-metadata.md`,
  `docs/adr/016-tag-output-filtering.md`,
  `docs/adr/017-background-colors.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/render.py`, `zotero_hmd_export/writer.py`,
  `zotero_hmd_export/cli.py`, `zotero_hmd_export/zotero.py`
- Tests: `tests/test_render.py`, `tests/test_writer.py`,
  `tests/test_zotero.py`, `tests/test_cli.py`
