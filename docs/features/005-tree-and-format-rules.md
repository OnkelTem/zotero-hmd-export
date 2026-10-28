# 005 — Tree and format rules

Status: done

## User story

As a researcher, I want to control block nesting and visual appearance by
annotation type, color, and tags, so that the exported page reflects the
structure of my reading.

## Acceptance criteria

- [x] `[tree]` supports absolute block levels `level1`…`level6`; `level1` is a
      top-level list item. Relative `rankN` rules are specified in feature 007.
- [x] Each nesting level adds two spaces of indentation.
- [x] `[format]` supports `normal`, `h1`…`h6`, `bold`, `italic`,
      `bold_italic`, `strikethrough`, `code`, `underline`, and `pug(...)`.
- [x] Tree and format resolve independently: a heading does not create nesting,
      and a tree level does not imply a heading.
- [x] Predicates combine annotation type (`h`/`highlight` or `u`/`underline`),
      color, and `#tag` conditions with AND.
- [x] No tree or format rules are active unless they are present in the project
      config.
- [x] An empty `[tree]` leaves annotations as content at the current level; an
      empty `[format]` renders text as `normal`.
- [x] The generated config shows example rules only as comments.
- [x] A rule with a tag beats a rule without a tag; within a tier, more
      conditions win; ties use the latest matching tag, then later config order.
- [x] `normal` is the fallback format and resets formatting when its rule wins.
- [x] `pug(...)` wraps text in a `span` with class, id, and one inline style;
      attribute values and text are HTML-escaped.
- [x] Empty text renders the literal `null`; comments remain nested.

## Out of scope

- Full Pug/Jade template support.
- Combining several formats in one rule.
- Image and ink annotations.

## References

- ADRs: `docs/adr/009-tree-and-format-rules.md`,
  `docs/adr/012-no-implicit-tree-format-defaults.md`,
  `docs/adr/013-relative-tree-levels.md`
- Related feature: `docs/features/007-relative-tree-levels.md`
- Specification: `docs/output-format.md`
- Code: `zotero_hmd_export/rules.py`, `zotero_hmd_export/render.py`
- Tests: `tests/test_rules.py`, `tests/test_render.py`
