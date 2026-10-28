# ADR 015: Configurable source metadata

Status: Accepted
Date: 2026-10-25

## Context

The renderer always appended `— [стр. N](zotero://...)` to every annotation. The
label was hardcoded in Russian, the link appeared on every paragraph, and there
was no way to keep only occasional page references. The user wants source
metadata to be opt-in, configurable by scope and frequency, and available both
inline and on a continuation line inside the same block.

## Decision

- Add an optional `[source]` table.
- When the table is absent or empty, `scope = "none"` and no source output is
  produced. There is no separate `enabled` flag.
- Fields:
  - `scope`: `none`, `all`, `level`, or `tree`. `level` limits source output
    to annotations matched by an absolute `levelN` rule. `tree` includes both
    `levelN` and `rankN` matches.
  - `when`: `block` or `page_change`.
  - `min_page_gap`: non-negative integer. `0` or `1` means any page change.
    Larger values require at least that numeric page distance. Non-numeric page
    labels fall back to any page change.
  - `link`: `true` wraps the label in a Markdown link using `desktopURI`;
    `false` emits only the label.
  - `placement`: `inline` appends to the block line; `next_line` emits a
    continuation line inside the same block, indented two spaces beyond the
    bullet.
  - `template`: the visible source line; supports `{label}`.
  - `page_label`: the link/label text; supports `{page}`.
- `when = "page_change"` compares against the last page for which a source line
  was actually emitted, not the immediately previous annotation. A skipped
  content block does not consume a page.
- If `page_label` is empty, or `desktopURI` is empty while `link = true`, no
  source line is emitted. There is no `open_label` fallback.
- `next_line` output is block content, not a child block. It does not make a
  block a parent for `collapsed:: true`.
- Templates allow only `{page}` in `page_label` and only `{label}` in
  `template`. Unknown placeholders, unbalanced braces, and embedded newlines
  are config errors.
- The property order for `next_line` is: block line, `collapsed:: true`, source
  line, comment, children.

## Alternatives

- **Hardcoded label with a boolean switch**: rejects the language problem and
  keeps per-paragraph links.
- **A single full suffix template** with `{page}` and `{url}`: more flexible but
  easier to break Markdown and duplicates the link wrapping logic.
- **A child block for source**: changes hierarchy, counts as a child for
  collapse, and can be hidden by the parent's collapsed state. Rejected.
- **A separate `enabled` flag**: duplicates `scope = "none"`.
- **Comparing to the previous annotation's page**: with `scope = "level"` or
  `"tree"`, a content block before the first eligible block on a page would
  consume the page and suppress the useful link.

## Consequences

- Source metadata is disabled by default. Existing projects lose links until
  they add `[source]` with a non-`none` scope.
- Page labels are configurable and no longer hardcoded in the renderer.
- One link per page or per page gap is possible without changing hierarchy.
- `next_line` keeps source information visible when the block is collapsed.
- The golden fixture is updated for the no-source default; source behavior is
  covered by targeted tests.
- The exact behavior is specified in `docs/output-format.md`.
