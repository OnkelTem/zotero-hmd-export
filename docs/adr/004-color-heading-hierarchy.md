# ADR 004: Color-based heading hierarchy

Status: Superseded by ADR 009
Date: 2026-10-23

## Context

PDFs do not reliably contain outlines, and Zotero annotations do not store a
reference to a chapter or heading. The workflow uses highlight colors to mark
headings. Underlines are used for text. This works for any PDF without an outline.

## Decision

- Heading annotations must be highlights with a heading color and non-empty text.
- The default heading colors map to absolute levels: Yellow=H2, Red=H3, Green=H4,
  Blue=H5, Purple=H6. H1 stays unused.
- Heading levels are read from `colors.heading` in the global/project config and
  passed to the renderer. Duplicate levels are rejected.
- Text annotations are underlines or any non-heading annotation type.
- Headings are list items: `- ## Heading`.
- Text/comments keep the current formatting: indentation, metadata continuation,
  `==...==` comments, `#[[...]]` tags, `<br>` line breaks, no blank lines.
- The color scheme is the source of hierarchy; PDF outlines are not used in v1.

## Consequences

- The user must mark headings with highlight colors and text with underlines.
- A missed or wrongly colored heading changes the generated hierarchy.
- Heading levels above H6 are not supported.
- The exact formatting rules are in `docs/output-format.md`.
