# ADR 001: Use Better BibTeX JSON-RPC for Zotero access

Status: Accepted  
Date: 2026-10-23

## Context

The previous Obsidian pipeline used `Zotero Integration` 3.2.1. Its code calls
Better BibTeX JSON-RPC at `127.0.0.1:23119` (`item.export`,
`item.attachments`, `cayw`) and does not read `zotero.sqlite`. That approach
works while Zotero is running and avoids database locks and schema coupling.

## Decision

Use Better BibTeX JSON-RPC as the only Zotero data source. Require Zotero 7 and
Better BibTeX to be running.

## Consequences

- No direct SQLite dependency.
- The tool only works while Zotero is running.
- Item selection can use BBT `cayw` or an explicit `--citekey`.
- API details are documented in `docs/zotero-bbt.md`.
