# ADR 009: Separate tree levels from visual formats

Status: Superseded in part by ADR 010, ADR 012, ADR 013, ADR 015, and ADR 016
Date: 2026-10-24

## Context

The first renderer treated a heading color as both the block hierarchy and the
visual heading level. That made tags unable to add formatting without changing
structure, and made a visual heading necessarily create nesting. The user wants
block hierarchy and appearance to be independent: a tag or color can assign a
tree level, a format, or both.

The user also wants the available options to be discoverable in the config.

## Decision

- Replace `[colors.heading]` and `[colors.text]` with `[tree]` and `[format]`.
- `[tree]` maps `Level1`…`Level6` to predicates; `Level1` is a top-level list
  item.
- `[format]` maps predicates to exactly one format: `normal`, `h1`…`h6`, a
  Markdown style, or `pug(...)`.
- Predicates combine annotation type (`h`/`u` or full names), color, and tags
  with AND. Tags are written `#tag` and normalized by removing one leading `#`.
- Tree and format resolve independently. A tree rule does not create a heading,
  and a heading format does not change nesting.
- A rule with a tag beats a rule without a tag. Within a tier, more conditions
  win; ties use the latest matching tag, then later config order.
- Formatting is a single winner; there is no list of combined formats. Use Pug
  CSS for arbitrary visual combinations.
- Empty text renders the literal `null`; a comment remains a nested
  `- ==...==` item. Image and ink annotations are skipped.
- Metadata is inline at the end: `— [стр. N](url)` or `— [открыть](url)`.
- The packaged template is the body used to create a complete project config
  (ADR 010).
- When a project tree table moves a predicate to another level, the old built-in
  or project mapping is removed rather than left as an ambiguous duplicate.

## Consequences

- Tags can change visual formatting or hierarchy independently; a tag format no
  longer silently demotes a block.
- A visual heading no longer creates a parent for following content unless a
  tree rule also matched.
- The default behavior remains Yellow=Level1/h2, Red=Level2/h3, Green=Level3/h4,
  Blue=Level4/h5, Purple=Level5/h6. These built-in defaults were later removed
  by ADR 012.
- Rule mistakes are config errors; duplicate predicates are rejected after
  merging.
- This supersedes ADR 004. The global-config part is superseded by ADR 010.
  Relative tree levels are added by ADR 013. Hardcoded inline metadata is
  replaced by configurable source metadata in ADR 015, and always-on tags are
  replaced by tag filtering in ADR 016.
