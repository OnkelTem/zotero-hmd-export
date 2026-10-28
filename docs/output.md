# Output pages

The exporter writes plain Markdown files into a project-configured directory.
A Logseq Markdown graph's `pages` directory is a typical target, but the writer
does not depend on any application-specific API.

## Output directory

```toml
[project]
output_dir = "/path/to/logseq/graph/pages"
```

- The path points directly to the final directory.
- The tool does not append `pages` and does not infer a graph root.
- The directory must already exist.
- Relative paths are resolved relative to the project config file.

## Filename templates

Project default:

```toml
[project]
file_name = "books___{author}___{title}.md"
```

Per-book override:

```toml
[[books]]
citekey = "Kleppmann2017Designing"
file_name = "reading_notes___kleppmann.md"
```

Precedence:

1. book `file_name`;
2. project `[project].file_name`;
3. built-in `{title}.md` when the project field is omitted.

The override is complete; templates are not merged.

## Placeholders

Allowed: `{author}`, `{title}`, `{citekey}`.

- Used placeholder with an empty value: error for the whole export, before any
  files are written.
- Unused placeholder with an empty value: ignored.
- Unknown placeholder: error.
- Format specifiers and conversions are not supported.
- `citekey` is always required to fetch annotations, even when it is not used in
  `file_name`.

## Literal namespace separators

The template is written as-is except for substituted values. For Logseq page
namespaces, write the separator yourself:

```
books___{author}___{title}.md
```

The tool does not replace `/` with `___`. A literal `/` in the final filename is
rejected because it would create a subdirectory.

Substituted values are normalized:

- `/` becomes `-`;
- `: ? " * < > | \ # %` are percent-encoded;
- spaces, non-ASCII letters, dots, commas, and parentheses are preserved;
- literal text (including `%XX` and `___`) is not re-encoded.

If the rendered name does not end with `.md`, `.md` is appended.

## Writing

- Encoding: UTF-8.
- Newlines: `\n`; exactly one trailing newline at EOF.
- Atomic write: temporary file in the same directory, then `os.replace()`.
- Existing page content is compared before writing:
  - identical content → `unchanged`, no write;
  - different content and `on_existing = "overwrite"` → write;
  - different content and `on_existing = "error"` → fail before writing.
- Export validates all books and renders all pages before writing anything. A
  validation, fetch, or render error leaves the output untouched.

## Optional properties

If `include_properties = true`, each page starts with:

```
citationKey:: <citationKey>
zotero-item:: <itemKey>
```

No blank line follows. Default is `false`.

## Consumer refresh

An application watching the output directory may not refresh an already-open
page immediately. If a page does not update, close and reopen it or trigger the
application's re-index command. The writer does not assume any UI state.

## Overwrite policy

The page is regenerated from scratch on every changed export. Manual edits inside
a generated page are lost. This is recorded in ADR 005; `on_existing = "error"`
is available when silent overwrite is undesirable.
