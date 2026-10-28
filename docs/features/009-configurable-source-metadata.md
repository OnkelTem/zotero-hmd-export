# 009 — Configurable source metadata

Status: done

## User story

As a researcher, I want source page references to be optional and configurable,
so that generated pages do not repeat a Zotero link on every paragraph while
still allowing a quick jump to the source when needed.

## Acceptance criteria

- [x] Source output is disabled when `[source]` is absent or has
      `scope = "none"`.
- [x] `scope` supports `none`, `all`, `level`, and `tree`.
- [x] `scope = "level"` includes only absolute `levelN` matches;
      `scope = "tree"` includes both `levelN` and `rankN`.
- [x] `when` supports `block` and `page_change`.
- [x] `when = "page_change"` compares against the last page whose source was
      actually emitted.
- [x] `min_page_gap` supports numeric page thresholds; non-numeric labels fall
      back to any page change.
- [x] `link = true` emits a Markdown link; `link = false` emits plain text.
- [x] `placement` supports `inline` and `next_line`.
- [x] `next_line` is content inside the same block, not a child block.
- [x] `template` supports `{label}`; `page_label` supports `{page}`.
- [x] Missing page labels and missing URLs with `link = true` omit the source.
- [x] Unknown placeholders, unbalanced braces, and embedded newlines are config
      errors.
- [x] Source lines appear after `collapsed:: true` and before comments/children.
- [x] The golden fixture reflects the no-source default.

## Out of scope

- Source lines as child blocks.
- Full Markdown suffix templates with `{url}`.
- Per-predicate source rules.
- A separate `enabled` flag.

## References

- ADR: `docs/adr/015-configurable-source-metadata.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`,
  `zotero_hmd_export/config.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`,
  `tests/test_config.py`, `tests/test_cli.py`
