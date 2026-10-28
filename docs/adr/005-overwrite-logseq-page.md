# ADR 005: Overwrite an existing output page

Status: Accepted  
Date: 2026-10-23

## Context

The user wants the export to be a deterministic projection of the current Zotero
annotations. Preserving or merging manual edits would require block-level
identity, conflict handling, and a persistent state store.

## Decision

Default `on_existing` is `"overwrite"`: a changed page is replaced completely.
`on_existing = "error"` is supported for users who prefer a hard failure when a
different page already exists. Export validates, fetches, and renders all books
before writing, so validation, fetch, and render errors leave the output
untouched.

## Consequences

- Re-running is idempotent for the same annotation set (content is compared).
- Any manual edits in the generated page are lost under `overwrite`.
- Users who need manual notes should keep them in a different page.
- A preserve/merge mode would require a new ADR and a stable block identity
  scheme.
