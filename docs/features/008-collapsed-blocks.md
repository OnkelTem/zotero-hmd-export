# 008 — Collapsed Logseq blocks

Status: done

## User story

As a researcher, I want blocks with children to be collapsed in Logseq, globally
or selectively by annotation type, color, and tag, so that generated pages open
with a manageable outline.

## Acceptance criteria

- [x] `[logseq.collapse]` accepts a boolean `default` and predicate rules with
      boolean values.
- [x] The built-in default is `false`; an absent or empty table changes nothing.
- [x] `true` collapses matching blocks; `false` expands them and overrides
      `default`.
- [x] Predicate priority is the same as for `[tree]` and `[format]`.
- [x] Collapse is independent of tree levels and visual formats.
- [x] `collapsed:: true` is emitted immediately after the block line, indented
      two spaces beyond the block bullet.
- [x] Only blocks with children receive the property.
- [x] A nested block or a non-empty comment counts as a child.
- [x] Leaf blocks never receive the property, even when a rule matches.
- [x] Absolute levels, relative ranks, and content blocks all support collapse.
- [x] Duplicate predicates and non-boolean values are config errors.
- [x] `levelN` and `rankN` are not valid `[logseq.collapse]` keys; use the
      predicates that define those levels.

## Out of scope

- Per-page collapse properties.
- Other Logseq properties.
- Arrays of selectors or wildcard predicates.
- Addressing collapse directly by absolute level or relative rank.

## References

- ADR: `docs/adr/014-collapsed-blocks.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`,
  `zotero_hmd_export/config.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`,
  `tests/test_config.py`, `tests/test_cli.py`
