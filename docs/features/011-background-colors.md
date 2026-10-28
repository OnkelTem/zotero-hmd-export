# 011 — Background colors by annotation or nesting level

Status: done

## User story

As a researcher, I want to color generated blocks either by their Zotero
annotation color or by their nesting level, so that I can compare the outline
with the PDF and inspect the generated hierarchy.

## Acceptance criteria

- [x] `[logseq.background]` has `mode = "off" | "annotation" | "level"` and an
      optional `palette`.
- [x] `mode = "off"` and a missing section produce no colors.
- [x] `mode = "annotation"` colors every annotation block by its Zotero color,
      including content blocks.
- [x] Zotero Magenta maps to Logseq `pink`.
- [x] Missing or unknown annotation colors produce no background property.
- [x] `mode = "level"` colors only `[tree]`-matched blocks, including `rankN`.
- [x] Level colors use `palette[(level - 1) % len(palette)]`.
- [x] `palette` is required for `mode = "level"` and is validated against named
      Logseq background colors.
- [x] `background-color:: <color>` is emitted after `collapsed:: true` and
      before next-line source and comments.
- [x] Comments and source lines are not colored.
- [x] The property does not affect collapse child detection.
- [x] Exact Zotero hex colors are out of scope.

## Out of scope

- Exact hex colors or custom CSS.
- Coloring comments.
- Per-predicate background rules.
- A separate `enabled` flag.

## References

- ADR: `docs/adr/017-background-colors.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`,
  `zotero_hmd_export/config.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`,
  `tests/test_config.py`, `tests/test_cli.py`
