# ADR 013: Relative tree levels

Status: Accepted
Date: 2026-10-25

## Context

`[tree]` originally offered only absolute `level1`…`level6` rules. Reusing a
color pair at a different depth required redefining absolute levels, and a
heading color always referred to the same global depth. The user wants to mark
text with colors that mean "one level deeper than the current block" so the
same color scheme can be reused anywhere in the document.

## Decision

- `[tree]` accepts `rank1`, `rank2`, … alongside `level1`…`level6`.
- `levelN` stays absolute: a match sets the level, the base for following
  relative rules, and clears the relative stack.
- `rankN` is a relative ordering, not an absolute depth.
  - The first relative rule starts at `base + 1`.
  - The same rank as the active one produces a sibling.
  - A higher rank produces a child of the nearest lower active rank.
  - A lower rank pops back to that ancestor; a rank without an active ancestor
    also starts at `base + 1`.
- `base` is the level of the most recent absolute `levelN` match, or `0` if no
  absolute rule has matched.
- A new absolute `levelN` match resets the relative stack.
- `rank` numbers may be skipped. Gaps affect ordering only, not depth:
  `rank1` then `rank3` produce levels 1 and 2, not 1 and 3.
- Relative depth is not capped at six. Absolute keys remain `level1`…`level6`,
  but a relative chain can produce level 7 and deeper. `[format]` still caps
  heading formats at `h6`.
- Existing predicate specificity and priority apply across absolute and
  relative rules. The winning rule's kind decides whether it sets a base or
  advances the relative stack.
- A predicate may appear only once in `[tree]`, whether in a `levelN` or a
  `rankN` rule.
- `[format]` remains independent and may target the same predicates.
- No relative behavior exists unless at least one `rankN` key is present.

## Alternatives

- **Additive offsets** (`+1` to the current level): repeated same-rank blocks
  would nest forever, so equal colors could not produce siblings.
- **Explicit parent links** (Red is a child of Yellow): flexible but verbose,
  and every color pair must be declared separately.
- **A separate `[tree.relative]` table**: rejected in favor of keeping
  absolute and relative rules next to each other in `[tree]`.
- **Cap relative depth at six**: rejected because text blocks do not need
  headings and the user wants unbounded relative nesting.

## Consequences

- The same colors can mark siblings and children at any depth.
- Rank numbers express ordering, not depth; the first relative block always
  starts at `base + 1`, even if its rank is greater than 1.
- A color used both absolutely and relatively needs distinct predicates, for
  example `h,Red` and `u,Red`.
- Relative-only configurations are valid and start from base 0.
- The specification lives in `docs/output-format.md`.
