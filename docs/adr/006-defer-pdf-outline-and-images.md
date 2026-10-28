# ADR 006: Defer PDF outline and image annotations

Status: Accepted  
Date: 2026-10-23

## Context

Two alternative ideas were explored:

1. Add an outline/bookmarks to the PDF and use it as the source of hierarchy.
2. Import rectangle/image annotations from the PDF.

Both add significant complexity: PDF editing, page/position mapping, a PDF
library, and image extraction. The tree/format rule scheme already provides a
reliable hierarchy for annotated books, and most annotations in the current
workflow are textual.

## Decision

Do not implement PDF outline creation or image/rectangle annotation export in
v1. Ignore image and ink annotations; use `[tree]` rules for hierarchy.

## Consequences

- No PDF library or PDF editing step is required.
- The user marks hierarchy blocks with type/color/tag `[tree]` rules.
- Image, ink, and rectangle annotations are not exported.
- Either feature can return with a separate ADR.
