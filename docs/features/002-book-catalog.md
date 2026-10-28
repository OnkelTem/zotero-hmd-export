# 002 — Book catalog

Status: done

## User story

As a researcher, I want to register Zotero books by citation key or through the
Zotero picker, so that each export processes the same set of books without a new
selection every time.

## Acceptance criteria

- [x] `add` stores the citation key, library ID, title, and author in
      `books.toml`.
- [x] `add --citekey` adds a book without opening the picker.
- [x] `add --update` refreshes stored Zotero metadata.
- [x] A manually entered author is preserved when Zotero has no author.
- [x] Adding an existing citation key does not create a duplicate entry.
- [x] `add` fails after saving the entry when a used filename placeholder has an
      empty value.

## Out of scope

- Automatic background updates when Zotero metadata changes.
- Removing books from the catalog.

## References

- ADRs: `docs/adr/007-project-local-config-and-books.md`
- User docs: `README.md` (Books)
- Code: `zotero_hmd_export/books.py`, `zotero_hmd_export/cli.py`,
  `zotero_hmd_export/zotero.py`
- Tests: `tests/test_books.py`, `tests/test_cli.py`
