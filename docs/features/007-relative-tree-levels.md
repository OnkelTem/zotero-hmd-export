# 007 — Relative tree levels

Status: done

## User story

As a researcher, I want colors to mark nesting relative to the current block,
so that I can reuse the same color scheme at any depth without assigning
absolute `levelN` values to every color.

## Acceptance criteria

- [x] `[tree]` accepts `rank1`, `rank2`, … alongside `level1`…`level6`.
- [x] A relative rule nests under the most recent absolute `levelN`, or under
      level 0 when no absolute rule has matched.
- [x] The same rank produces a sibling; a higher rank produces a child of the
      nearest lower active rank; a lower rank pops back to that ancestor.
- [x] A new absolute `levelN` resets the relative stack.
- [x] Rank gaps do not create depth gaps; the first relative block starts at
      `base + 1` regardless of its rank number.
- [x] Relative depth is not capped at six.
- [x] Existing predicate priority applies across absolute and relative rules;
      the winner's kind decides how the level is assigned.
- [x] `[format]` remains independent and can target relative predicates.
- [x] Duplicate ranks and duplicate predicates across absolute and relative
      rules are config errors.
- [x] Relative-only configurations work with base 0.
- [x] Empty text still renders the literal `null` and keeps the computed level;
      comments remain nested.
- [x] No relative behavior exists unless `rankN` keys are present.

## Out of scope

- Explicit parent links between colors.
- Additive `+N` offsets.
- Changing absolute `level1`…`level6` semantics.
- New visual formats.

## References

- ADR: `docs/adr/013-relative-tree-levels.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`,
  `tests/test_config.py`
