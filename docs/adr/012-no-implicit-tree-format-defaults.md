# ADR 012: No implicit tree or format defaults

Status: Accepted
Date: 2026-10-24

## Context

ADR 009 introduced separate `[tree]` and `[format]` layers and also defined
built-in defaults: Yellow mapped to level 1 and h2, Red to level 2 and h3, and
so on. Those defaults were merged into every project config, so a config without
`[tree]` or `[format]` still produced a hierarchy and formatted headings.

That behavior is surprising: the user sees a hierarchy that is not described by
the project config. A project that only wants flat annotations cannot disable
the defaults without overriding every built-in rule.

## Decision

- Use `[tree]` and `[format]` exactly as written in the project config.
- A missing or empty `[tree]` table means no tree rules; annotations stay at
  the current level.
- A missing or empty `[format]` table means no format rules; text is rendered
  as `normal`.
- Remove `DEFAULT_TREE_SPEC`, `DEFAULT_FORMAT_SPEC`, and the merge logic that
  combined them with project tables.
- The generated config shows tree and format examples only as comments. They
  are not active until the user uncomments and edits them.
- `render_item` without explicit rules renders flat content with `normal`
  formatting.

## Consequences

- A fresh project exports flat annotations until the user defines rules.
- No hierarchy or formatting is created implicitly.
- Rule examples remain discoverable in the generated config and in
  `docs/output-format.md`.
- Duplicate predicates are still rejected within the project table.
- This supersedes the default tree and format mapping in ADR 009.
