# ADR 014: Collapsed Logseq blocks

Status: Accepted
Date: 2026-10-25

## Context

Logseq can store a collapsed state on a block. The generated Markdown uses a
Logseq graph as its primary target, and the user wants to collapse blocks with
children by default, with per-color and per-tag exceptions.

Collapse is neither a tree level nor a text format. It is a block property that
only makes sense when the block has children. Mixing it into `[tree]` or
`[format]` would overload those layers, complicate value parsing (especially
`pug(...)`, which may contain commas), and make it impossible to control content
blocks that did not match a tree rule.

## Decision

- Add a `[logseq.collapse]` table.
- `default` is a boolean; the built-in default is `false`, so existing output
  does not change unless the table opts in.
- Every other key is a predicate with the same syntax and priority as `[tree]`
  and `[format]`. Values are booleans: `true` collapses, `false` expands.
- A matching rule overrides `default`; the most specific rule wins using the
  existing predicate priority.
- Collapse is resolved per annotation and is independent of tree and format.
  A block can be a heading, bold, and collapsed at the same time.
- Emit `collapsed:: true` as a block property line immediately after the block
  line, indented two spaces beyond the block bullet.
- Emit the property only when the block has at least one child.
  - A child is a following block with greater indentation or a non-empty
    comment.
  - Leaf blocks never receive the property, even when a rule or `default`
    says `true`.
- A block whose collapse decision is `false` gets no property; absence means
  expanded in Logseq.
- Duplicate collapse predicates and non-boolean values are config errors.
- The configuration accepts only predicates. Level-based control uses the same
  predicates that define the tree level; `levelN` and `rankN` keys are not part
  of `[logseq.collapse]`.

## Alternatives

- **Append `collapsed` to `[format]` values** (`"h3,collapsed"`): convenient but
  conflates visual format with block state, requires splitting values with
  comma-sensitive `pug(...)` syntax, and needs a dummy format for plain text.
- **Append `collapsed` to `[tree]`** (`level1 = "h,Yellow,collapsed"`): mixes
  hierarchy with block state and cannot control content blocks without a tree
  rule.
- **`[logseq]` arrays** (`collapsed = [...]`, `expanded = [...]`): compact but
  cannot express explicit per-predicate false overrides with the existing
  specificity rules without a second priority system.
- **A top-level `[collapse]` table**: simpler, but the user preferred grouping
  Logseq-specific settings under `[logseq]`.
- **A wildcard `"*" = true`**: unnecessary because `default` already provides a
  global fallback.

## Consequences

- `[logseq.collapse]` is a new optional config section.
- Existing projects and the golden fixture are unchanged when the section is
  absent or empty.
- Collapsing all blocks with children requires `default = true`; it is not an
  implicit behavior.
- Comments count as children, so a block with only a comment can be collapsed.
- Property lines are not list items; the output format now includes them.
- The exact behavior is specified in `docs/output-format.md`.
