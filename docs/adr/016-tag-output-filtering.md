# ADR 016: Tag output filtering

Status: Accepted
Date: 2026-10-25

## Context

Every Zotero annotation tag was rendered inline as `#[[tag]]`. Some tags are
used only as selectors for `[tree]`, `[format]`, or `[logseq.collapse]`; when the
format already expresses the same information, the tag is redundant. Other tags
are meaningful and should stay in the output. The user wants explicit control
over which tags are printed.

## Decision

- Add an optional `[tags]` table.
- When the table is absent or empty, no tags are emitted.
- `default` is a boolean:
  - `false`: emit only tags listed in `show`;
  - `true`: emit all tags except those listed in `hide`.
- `hide` and `show` are arrays of tag names. One leading `#` is removed during
  normalization; comparison is case-sensitive.
- `show` with `default = true`, and `hide` with `default = false`, are config
  errors.
- Duplicate tag names in a list are config errors.
- Filtering affects output only. Hidden tags still participate in `[tree]`,
  `[format]`, and `[logseq.collapse]` rules. Source output may be affected only
  indirectly when `[source] scope` is `"level"` or `"tree"` and follows the tree
  result.
- Tags remain inline on the block line, before source metadata.

## Alternatives

- **Automatically hide tags used by a matching rule**: unsafe because a tag can
  be both a selector and a semantic marker.
- **Global `include_tags` boolean**: cannot keep selected semantic tags while
  hiding control tags.
- **Predicate rules for tag output**: more flexible but unnecessarily complex
  for a per-tag decision.
- **Keep printing all tags**: retains redundancy and forces manual cleanup in
  the target graph.

## Consequences

- Tags are disabled by default. Existing projects lose tags until they add
  `[tags]`.
- To keep the previous output, use `default = true` with no `hide` list.
- Control tags can be hidden without losing the formatting or hierarchy they
  select.
- The golden fixture is updated for the no-tags default; filtering is covered by
  targeted tests.
- The exact behavior is specified in `docs/output-format.md`.
