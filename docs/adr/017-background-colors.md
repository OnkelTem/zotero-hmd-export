# ADR 017: Background colors by annotation or nesting level

Status: Accepted
Date: 2026-10-25

## Context

The user needs to compare the generated outline with the colored annotations in
the PDF. The output has no colors, so matching a block to its source is hard.
The user also wants an optional view of the hierarchy where each nesting level
gets a color from the Zotero palette.

`[format]` cannot provide this: it selects exactly one visual format, and a
color span would replace a heading or bold format. Logseq block background is a
separate block property (`background-color::`) and is independent of headings,
formatting, source metadata, and collapse state.

## Decision

- Add an optional `[logseq.background]` table.
- `mode` is `off`, `annotation`, or `level`. The default is `off`. No separate
  `enabled` flag is needed.
- `mode = "annotation"` colors every annotation block by its Zotero color:
  Yellow→yellow, Red→red, Green→green, Blue→blue, Purple→purple,
  Magenta→pink, Orange→orange, Gray→gray. This includes content blocks and is
  intended for comparison with the PDF.
- `mode = "level"` colors only blocks matched by `[tree]`, including `rankN`
  blocks. The color is selected from `palette` by the computed absolute level:
  `palette[(level - 1) % len(palette)]`. Content blocks without a tree rule are
  not colored.
- `palette` is required for `mode = "level"` and used only by that mode. When
  present in other modes it is still validated but has no effect.
  Colors are named Logseq background colors: `yellow`, `red`, `green`, `blue`,
  `purple`, `pink`, `orange`, `gray`. Values are normalized to lowercase.
- Emit `background-color:: <color>` as a block property line immediately after
  `collapsed:: true` (if present) and before a next-line source and comments.
- The property applies to the block itself. Comments and next-line source lines
  are not colored.
- A block without a known annotation color gets no background property in
  annotation mode.
- Exact Zotero hex values are not supported by this mechanism. Logseq's named
  palette is used; exact colors would require custom CSS or inline spans.

## Alternatives

- **Color text through `[format] pug(...)`**: conflicts with heading and other
  formats, and does not color the block background.
- **Only `mode = "annotation"`**: useful for source comparison but cannot show
  computed depth.
- **Only `mode = "level"`**: does not work for comparing relative blocks whose
  annotation colors differ from their computed level color.
- **A separate `enabled` flag**: duplicates `mode = "off"`.
- **An explicit `levelN`/`rankN` → color table**: more verbose and cannot handle
  relative depth above the palette without additional rules.
- **Exact hex colors**: would require inline CSS or custom graph CSS and is
  outside the block-property approach.

## Consequences

- Background colors are disabled by default and do not change existing output.
- Annotation mode makes the outline directly comparable to the PDF, at the cost
  of being visually noisy.
- Level mode shows hierarchy but intentionally differs from the annotation
  colors for relative blocks.
- Palette cycling handles arbitrary depth.
- The golden fixture is unchanged while the section is absent.
- The exact behavior is specified in `docs/output-format.md`.
