# ADR 008: Filename templates and placeholder validation

Status: Accepted  
Date: 2026-10-23

## Context

Page filenames need full user control, including application namespace
separators. The user wants a project template, a per-book override, and clear
failure when a used metadata value is absent. The tool must not reimplement a
consumer's page-name rules.

## Decision

- `file_name` precedence: book override, then project, then the built-in
  `{title}.md`. Overrides are complete; templates are not merged.
- Allowed placeholders: `{author}`, `{title}`, `{citekey}`. Unknown placeholders,
  format specifiers, and conversions are rejected.
- A used placeholder with an empty value is an error. An unused empty value is
  ignored. `citekey` is always required for fetching annotations.
- Literal template text is preserved. The tool does not convert `/` to `___`;
  the user writes the namespace separator directly. A literal `/` in the final
  name is rejected.
- Substituted values normalize `/` to `-` and percent-encode
  `: ? " * < > | \ # %`. Literal `%XX` sequences are not re-encoded.
- `.md` is appended when missing.
- Validation runs for every book before any page is written.

## Consequences

- The user controls application-specific page names without tool-side mapping.
- Missing metadata fails early with an actionable message.
- A per-book literal filename is possible and needs no author/title.
- Percent-encoding rules are documented and covered by tests.
