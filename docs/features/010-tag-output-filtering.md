# 010 — Tag output filtering

Status: done

## User story

As a researcher, I want to hide tags that only select tree, format, or collapse
rules while keeping semantic tags, so that generated pages do not repeat
redundant markers.

## Acceptance criteria

- [x] Tag output is disabled when `[tags]` is absent or empty.
- [x] `default = true` emits all tags except those in `hide`.
- [x] `default = false` emits only tags in `show`.
- [x] `show` with `default = true` and `hide` with `default = false` are config
      errors.
- [x] Tag names are normalized by removing one leading `#`; comparison is
      case-sensitive.
- [x] Duplicate names in `hide` or `show` are config errors.
- [x] Hidden tags still participate in `[tree]`, `[format]`, and
      `[logseq.collapse]`; source follows `scope = "level"` or `"tree"` via the
      tree result.
- [x] Visible tags remain inline before source metadata.
- [x] The golden fixture reflects the no-tags default.

## Out of scope

- Automatic hiding of tags used in matching rules.
- Per-annotation tag output rules.
- Moving tags to block properties.

## References

- ADR: `docs/adr/016-tag-output-filtering.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`,
  `zotero_hmd_export/config.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`,
  `tests/test_config.py`
