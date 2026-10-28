# Output format

This is the exact specification for the generated Logseq Markdown. Python
renders the list directly; there is no template engine.

## Input

Annotations come from Better BibTeX `item.attachments`. The relevant fields:

| Field | Meaning |
|---|---|
| `type` | `highlight`, `underline`, `note`, `image`, `ink`, etc. |
| `colorCategory` | `Yellow`, `Red`, `Green`, `Blue`, `Purple`, `Magenta`, `Orange`, `Gray` |
| `annotatedText` | Highlighted/underlined text |
| `comment` | Annotation comment |
| `pageLabel` | Printed/page label shown by Zotero |
| `desktopURI` | `zotero://open-pdf/...` link |
| `tags` | Array of `{ "tag": "..." }` |
| `annotationSortIndex` | Document-order sort key |
| `key` | Annotation key |
| `imageRelativePath` | Image path for rectangle annotations; out of scope in v1 |

Annotations are sorted by `annotationSortIndex` (lexicographic; BBT uses
zero-padded components).

## Output layers

- `[tree]` assigns a block nesting level, either absolute or relative.
- `[format]` assigns a visual format.
- `[logseq.collapse]` assigns a Logseq collapsed state.
- `[logseq.background]` assigns Logseq block background colors.
- `[source]` assigns source page metadata.
- `[tags]` filters whether annotation tags are printed.

They are resolved separately. A tree rule never creates a heading, a format
rule never changes nesting, and collapse never changes hierarchy or appearance.
Background, source, and tag settings do not affect tree construction or
formatting.

```toml
[tree]
level1 = "h,Yellow"
level2 = "h,Red"

[format]
"h,Yellow" = "h2"
"h,Red" = "h3"
```

With this config, a Yellow highlight is a top-level block and looks like
`## Heading`. A Red highlight is nested and looks like `### Heading`. Changing
`[format]` to `bold` would keep the same nesting but render a bold text block
instead of a heading.

Relative `rankN` rules can be mixed into the same `[tree]` table; they are
described under [Tree rules](#tree-rules). Collapse is described under
[Collapsed blocks](#collapsed-blocks), background colors under
[Background colors](#background-colors), source metadata under
[Source metadata](#source-metadata), and tags under [Tag output](#tag-output).

## Predicates

Tree, format, and collapse rules use the same predicate syntax:

- `h` or `highlight` — highlight annotation;
- `u` or `underline` — underline annotation;
- `Yellow`, `Red`, … — color, case-insensitive;
- `#tag` — tag.

Only highlights and underlines can be matched by type. Other Zotero annotation
types are not valid predicate conditions.

Conditions are comma-separated and ANDed. A rule may have type, color, and
multiple tags:

```toml
[tree]
level1 = "u,Red"
level3 = "#tag3"
level4 = "h,Yellow,#tag1"

[format]
Red = "bold"
"u,Blue,#tag1" = 'pug(.note(style="color:blue"))'
```

- Type aliases are canonicalized to `highlight` and `underline`.
- Colors are canonicalized to the Zotero names.
- A leading `#` on a target tag or a config tag is removed before comparison.
- Tag comparison is case-sensitive after removing one leading `#`.
- TOML keys containing `#` or commas must be quoted.
- Invalid conditions, conflicting types/colors, and empty predicates are config
  errors.

## Tree rules

`[tree]` has two kinds of keys with the same predicate syntax and priority:

- absolute `level1`…`level6`;
- relative `rank1`, `rank2`, … .

A predicate may appear only once in `[tree]`, whether in an absolute or a
relative rule. Duplicate levels, duplicate ranks, and duplicate predicates are
config errors.

### Absolute levels

```toml
[tree]
level1 = "h,Yellow"
level2 = "h,Red"
level3 = "h,Green"
level4 = "h,Blue"
level5 = "h,Purple"
```

- Keys are `level1`…`level6`, case-insensitive.
- `level1` is a top-level list item, `level2` is nested, and so on.
- Levels may be skipped; output does not invent missing levels.
- No tree rules are active unless they are present in `[tree]`.
- If no tree rule matches, the annotation is content at the current level.
- An absolute match updates the current level even if the format is not a
  heading.
- An absolute match also sets the base for following relative rules and clears
  the relative stack.

### Relative ranks

```toml
[tree]
level1 = "h,Yellow"
rank1 = "h,Red"
rank2 = "h,Green"
```

- Keys are `rankN` with a positive integer `N`, case-insensitive. `rank1`,
  `rank2`, … define an ordering, not absolute depth.
- `base` is the level of the most recent absolute `levelN` match, or `0` when
  no absolute rule has matched.
- A relative match does not change `base`.
- The first relative match starts at `base + 1`, regardless of its rank.
- Repeated same rank is a sibling.
- A higher rank is one level deeper than the nearest lower active rank.
- A lower rank pops back to that ancestor. If no lower ancestor is active, it
  starts at `base + 1`.
- Rank numbers may have gaps. Gaps affect ordering only, not depth: `rank1`
  then `rank3` produce levels 1 and 2, not 1 and 3.
- Relative depth is not capped at six. A chain can produce level 7 and deeper;
  `[format]` still caps headings at `h6`.
- Relative rules work without any absolute rule.
- A new absolute `levelN` match resets the relative stack.

For each relative match with rank `R`:

1. Pop stack entries while their rank is `>= R`.
2. Use the top stack level as the parent, or `base` if the stack is empty.
3. Assign `parent + 1` as the level.
4. Push `(R, level)` onto the stack.

Example sequence with the config above:

| Annotation | Rule | Level |
|---|---|---|
| Yellow highlight | `level1` | 1 |
| Red highlight | `rank1` | 2 |
| Red highlight | `rank1` | 2 (sibling) |
| Green highlight | `rank2` | 3 |
| Red highlight | `rank1` | 2 (popped back) |

With `normal` formats for the relative colors, the output starts as:

```markdown
- ## Yellow
  - Red
  - Red
    - Green
  - Red
```

Absolute and relative rules share one priority order. When both kinds match,
the most specific rule wins, and its kind decides whether it sets a base or
advances the relative stack.

## Format rules

Allowed values:

| Value | Output |
|---|---|
| `normal` | plain text |
| `h1`…`h6` | `#`…`######` after the list marker |
| `bold` | `**text**` |
| `italic` | `*text*` |
| `bold_italic` | `***text***` |
| `strikethrough` | `~~text~~` |
| `code` | `` `text` `` |
| `underline` | `<u>text</u>` |
| `pug(...)` | `<span ...>text</span>` |

`hN` is a block prefix: the renderer emits `- ## text`; it is not inline
formatting. Only one format rule can win. `normal` is the fallback when no rule
matches; a matching `normal` rule resets formatting.

### Pug/Jade span

`pug(...)` wraps the text in a `<span>`. It supports class, id, and a single
inline style. The selector syntax follows Pug attributes:
<https://pugjs.org/language/attributes.html>.

```toml
[format]
"h,Yellow" = 'pug(.note#main(style="color:red"))'
```

Output:

```html
<span class="note" id="main" style="color:red">text</span>
```

- `.a.b` adds classes; `#id` adds an id.
- `span.note` is accepted; the wrapper is always `span`.
- `pug(style="color:blue")` is accepted without a selector.
- Text and attribute values are HTML-escaped. `<br>` line breaks produced from
  annotation newlines are preserved.
- CSS classes must be defined by the consumer; inline `style` is emitted
  directly.

No format rules are active unless they are present in `[format]`. When no rule
matches, the renderer uses `normal`.

## Rule priority

For the tree, format, and collapse layers independently:

1. A rule with a tag beats a rule without a tag.
2. Within the same tier, more conditions win.
3. On a tie, the rule matching the latest tag in the annotation wins.
4. If still tied, the rule declared later in the project config wins.

The same order applies across absolute and relative tree rules. A tag tree rule
therefore overrides a color tree rule, and the winning kind determines whether
the annotation sets a base level or advances the relative stack.

A tag rule therefore overrides a color format. If a Yellow highlight has tag
`#def` and `"#def" = "bold"`, it stays at `level1` but becomes a bold text
block, not a heading. To keep the heading, use `"h,Yellow,#def" = "h2"`.

## Collapsed blocks

Collapse is a Logseq block property, not a tree level or a visual format. It is
configured in a separate table:

```toml
[logseq.collapse]
default = false

"h,Yellow" = true
"h,Red" = true
"h,Yellow,#keep-open" = false
"#collapse-me" = true
```

- `default` is a boolean. When the table or `default` is absent, the built-in
  default is `false` and nothing is collapsed.
- Every other key is a predicate with the same syntax and priority as `[tree]`
  and `[format]`.
- A rule with `true` collapses matching blocks; a rule with `false` expands them
  and can override `default = true`.
- The most specific matching rule wins. A tag rule therefore beats a color or
  type rule.
- Collapse is independent of tree and format. A heading can also be bold and
  collapsed.
- `levelN` and `rankN` are not valid keys here. Use the predicates that define
  those levels.

A block is collapsible only when it has at least one child:

- a following block with greater indentation, or
- a non-empty comment.

The property is emitted only when the block is collapsed **and** has a child.
Leaf blocks never receive it, even when a rule or `default` says `true`. A block
without the property is expanded.

The property line is not a list item. It follows the block line immediately,
indented two spaces beyond the block bullet, before any comment or child:

```markdown
- ## Heading
  collapsed:: true
  - ==comment==
  - Child block
    collapsed:: true
    - Grandchild
```

## Background colors

Block background colors are controlled by `[logseq.background]` and emitted as
the Logseq block property `background-color::`.

```toml
[logseq.background]
mode = "off"          # off | annotation | level

# Required only for mode = "level":
palette = ["yellow", "red", "green", "blue", "purple", "pink", "orange", "gray"]
```

- A missing section or `mode = "off"` produces no colors.
- `mode = "annotation"` colors every annotation block by its Zotero color,
  including content blocks. Unknown or missing colors produce no property.
- `mode = "level"` colors only blocks matched by `[tree]`, including `rankN`.
  The color is `palette[(level - 1) % len(palette)]`. Content blocks without a
  tree rule are not colored.
- `palette` is required for `mode = "level"`. Colors are named Logseq
  backgrounds: `yellow`, `red`, `green`, `blue`, `purple`, `pink`, `orange`,
  `gray`.
- Annotation mode maps Zotero colors as follows:

| Zotero | Logseq |
|---|---|
| Yellow | yellow |
| Red | red |
| Green | green |
| Blue | blue |
| Purple | purple |
| Magenta | pink |
| Orange | orange |
| Gray | gray |

- The property line follows `collapsed:: true` when present, then next-line
  source and comments.
- Comments and source lines are not colored.
- Background does not affect tree construction, formatting, or collapse child
  detection.
- Exact Zotero hex colors are not supported; use the named Logseq palette.

Example with `mode = "annotation"`:

```markdown
- Text
  background-color:: yellow
  - Nested text
    background-color:: pink
```

## Source metadata

Source output is disabled unless `[source]` has a non-`none` scope.

```toml
[source]
scope = "all"             # none | all | level | tree
when = "page_change"      # block | page_change
min_page_gap = 0          # 0 = any page change; 10 = at least 10 numeric pages
link = true
placement = "next_line"   # inline | next_line
template = "— {label}"
page_label = "{page}"
```

- A missing `[source]` table or `scope = "none"` produces no source output.
- `scope = "all"` considers every annotation.
- `scope = "level"` considers only annotations matched by an absolute `levelN`
  rule. `scope = "tree"` considers annotations matched by any `[tree]` rule,
  both `levelN` and `rankN`.
- `when = "block"` emits on every eligible block. `when = "page_change"` emits
  only when the page differs from the last page whose source was actually
  emitted. Skipped blocks do not consume a page.
- `min_page_gap > 1` requires at least that numeric page distance between
  emitted sources. Non-numeric page labels fall back to any page change.
- `link = true` wraps the rendered label in a Markdown link using
  `desktopURI`. `link = false` emits only the label.
- A missing page label produces no source line. With `link = true`, a missing
  `desktopURI` also produces no source line.
- `template` supports `{label}`. `page_label` supports `{page}`. Unknown
  placeholders, unbalanced braces, and embedded newlines are config errors.
- `placement = "inline"` appends the source to the block line after tags.
- `placement = "next_line"` emits a continuation line inside the same block,
  indented two spaces beyond the block bullet. It is not a child block and does
  not affect collapse detection.
- For `next_line`, the order is block line, `collapsed:: true`, source line,
  comment, children.

Inline example:

```markdown
- ## Heading #[[tag]] — [7](zotero://...)
```

Next-line example:

```markdown
- ## Heading #[[tag]]
  collapsed:: true
  — [p. 7](zotero://...)
  - ==comment==
  - Child
```

## Tag output

Tags are disabled unless `[tags]` enables them.

```toml
[tags]
default = true
hide = ["bold", "heading"]

# Or:
# default = false
# show = ["important"]
```

- A missing `[tags]` table, an empty one, or `default = false` without `show`
  produces no tags.
- `default = true` emits all tags except those listed in `hide`.
- `default = false` emits only tags listed in `show`.
- `show` with `default = true`, and `hide` with `default = false`, are config
  errors.
- Tag names are normalized by removing one leading `#`; comparison is
  case-sensitive.
- Duplicate names in `hide` or `show` are config errors.
- Hidden tags still participate in `[tree]`, `[format]`, and
  `[logseq.collapse]`.
- Visible tags are emitted inline as `#[[tag]]` before source metadata.

## Rendering

`current_level = 0`, `base_level = 0`, and the relative stack is empty before
the first block.

For each annotation, after sorting:

1. Resolve the most specific tree rule.
   - No match: keep `current_level`.
   - Absolute `levelN`: set `current_level` and `base_level` to `N`, and clear
     the relative stack.
   - Relative `rankN`: pop stack entries with rank `>= N`; the parent is the
     top stack level or `base_level`; set `current_level = parent + 1`; push
     `(N, current_level)`.
2. `text` is `annotatedText`, trimmed, with newlines replaced by `<br>`.
3. If `text` is empty, use the literal `null`.
4. Resolve the format and apply it to `text`.
5. Filter visible tags according to `[tags]`.
6. Resolve the source line according to `[source]`. If placement is `inline`,
   append it after tags; if `next_line`, keep it for the block's continuation
   line. Update the last emitted source page only when a line is produced.
7. Resolve the collapse state.
8. Resolve the background color according to `[logseq.background]`.
9. Store the block line, its indentation, its normalized comment, its collapse
   state, its background, and its next-line source (if any).
10. Skip `image` and `ink` annotations.

After all annotations are collected, emit blocks in order:

1. Append the block line.
2. Determine whether the block has a child: a non-empty comment, or a following
   block with greater indentation.
3. If the block is collapsed and has a child, append
   `collapsed:: true` at the block indentation plus two spaces.
4. If the block has a background, append `background-color:: <color>` at the
   block indentation plus two spaces.
5. If the block has a next-line source, append it at the block indentation plus
   two spaces.
6. If the block has a comment, append it as a nested list item at the block
   indentation plus two spaces.

Indentation uses two spaces per level:

- block at level `N`: `2 * (N - 1)` spaces;
- content under current level `N`: `2 * N` spaces;
- comment on a block or content: block indentation plus two spaces;
- collapsed property: block indentation plus two spaces;
- background property: block indentation plus two spaces;
- next-line source: block indentation plus two spaces;
- content before the first block: `0` spaces.

The block line is:

```
{indent}- {formatted_text}{tags}{inline_source}
```

Comments:

```
{indent}- ==<comment>==
```

Collapsed property:

```
{indent}collapsed:: true
```

Background property:

```
{indent}background-color:: yellow
```

Next-line source:

```
{indent}{source_line}
```

The comment is trimmed and newlines become `<br>`.

## Source metadata and tags

- Tags are printed only when `[tags]` enables them. Visible tags are appended as
  `#[[tag]]`, space-separated.
- Source metadata is printed only when `[source]` has a non-`none` scope.
- An inline source follows tags: ` — [p. 7](url)`.
- A next-line source is a continuation line inside the block, not a child item.
- If `pageLabel` is empty, no source line is emitted.
- If `link = true` and there is no `desktopURI`, no source line is emitted.
- The annotation color is not printed as text. It may appear as a Logseq
  `background-color::` property when `[logseq.background]` enables it.
- There is no blockquote and no separate metadata block.

The examples below assume `[tags] default = true` and `[source]` with
`scope = "all"`, `when = "block"`, `placement = "inline"`, and
`page_label = "p. {page}"`:

```markdown
- ## Heading #[[tag]] — [p. 7](zotero://...)
  - ==heading comment==
  - *Red text* #[[tag]] — [p. 8](zotero://...)
    - ==content comment==
  - **Green text** — [p. 9](zotero://...)
  - `code text` — [p. 10](zotero://...)
  - <span class="asd" style="color:blue">custom</span> — [p. 11](zotero://...)
```

With `placement = "next_line"` the first block becomes:

```markdown
- ## Heading #[[tag]]
  — [p. 7](zotero://...)
  - ==heading comment==
```

## Empty text and comment-only annotations

If `annotatedText` is empty, the block text is the literal `null`. A comment is
still rendered as a nested list item. With source metadata enabled:

```markdown
- null — [p. 3](zotero://...)
  - ==note==
```

This applies to tree blocks and content. `image` and `ink` annotations are
skipped.

## Line breaks and blank lines

- Replace every newline in `annotatedText` and `comment` with `<br>`.
- Do not emit blank lines anywhere.
- `\n\n` becomes `<br><br>`, preserving the visual empty line.
- Join all lines with `\n` and write one trailing `\n` at EOF.

## Example

Example config:

```toml
[tree]
level1 = "h,Yellow"
level2 = "h,Red"
level3 = "h,Green"
level4 = "h,Blue"
level5 = "h,Purple"

[format]
"h,Yellow" = "h2"
"h,Red" = "h3"
"h,Green" = "h4"
"h,Blue" = "h5"
"h,Purple" = "h6"

[source]
scope = "all"
when = "block"
placement = "inline"
page_label = "p. {page}"

[tags]
default = true
```

Input (abridged):

- heading: Yellow, "Chapter 1. Two systems", comment "Section opener", page 7
- content: underline, page 7, tag `example`, comment "Why this matters"
- content: underline, page 8, tags `example`, `example.1`

Output:

```markdown
- ## Chapter 1. Two systems — [p. 7](zotero://open-pdf/library/items/BBBB2222?page=7&annotation=...)
  - ==Section opener==
  - A first supporting passage #[[example]] — [p. 7](zotero://open-pdf/library/items/BBBB2222?page=7&annotation=...)
    - ==Why this matters==
  - A second supporting passage #[[example]] #[[example.1]] — [p. 8](zotero://open-pdf/library/items/BBBB2222?page=8&annotation=...)
    - ==Another comment==
```

## Edge cases

- **Text before the first block**: top-level content at indent 0.
- **Skipped absolute level** (`level1` → `level3`): output `level3`
  indentation; do not invent `level2`.
- **First relative rule before any absolute rule**: base is 0, so the block is
  level 1 regardless of its rank number.
- **Rank gap** (`rank1` → `rank3`): the levels are consecutive; rank gaps do not
  create depth gaps.
- **Repeated rank**: siblings at the same level.
- **Lower rank with no active ancestor**: starts at `base + 1`.
- **New absolute level**: clears the relative stack before following rules.
- **Relative depth above 6**: valid for list nesting; heading formats still
  stop at `h6`.
- **Same color used absolutely and relatively**: use distinct predicates, for
  example `h,Red` and `u,Red`, because duplicate predicates are rejected.
- **Leaf block with a collapse rule**: no `collapsed:: true`; the decision is
  ignored because the block has no children.
- **Comment-only child**: a non-empty comment is enough to make the block
  collapsible.
- **`default = true` with a false rule**: the most specific `false` rule wins
  and the block stays expanded.
- **Collapse section absent or empty**: no property and no behavior change.
- **Background section absent or `mode = "off"`**: no background property.
- **Annotation background mode**: content blocks are colored too; unknown or
  missing colors produce no property.
- **Level background mode**: only `[tree]`-matched blocks are colored; content
  without a tree rule is not.
- **Palette shorter than depth**: colors cycle.
- **Empty palette with `mode = "level"`**: config error.
- **Comments and source lines**: never colored.
- **Property order**: `collapsed:: true`, then `background-color::`, then
  next-line source, then comment.
- **Source section absent or `scope = "none"`**: no source metadata.
- **`scope = "level"`**: only `levelN`-matched blocks get source; relative
  `rankN` blocks and content do not.
- **`scope = "tree"`**: both `levelN` and `rankN` blocks get source; content
  without a tree rule does not.
- **`when = "page_change"`**: only the first eligible block per page run gets a
  source; skipped blocks do not consume the page.
- **`min_page_gap`**: applies only to numeric page labels; non-numeric labels
  use any page change.
- **Missing page label**: no source line.
- **`link = true` with missing `desktopURI`**: no source line.
- **`link = false`**: source is plain text and does not require a URL.
- **`next_line` source**: a continuation line inside the block; it is not a child
  and does not affect `collapsed:: true`.
- **Tags section absent or empty**: no tags.
- **Hidden tag used by a rule**: the tag is not printed but still selects tree,
  format, collapse, or source behavior.
- **Unknown color**: content unless a matching tree rule exists.
- **Tree match without heading format**: logical block, plain text.
- **Heading format without tree match**: visual heading at the current level;
  it does not change nesting.
- **Empty text**: literal `null`.
- **Comment-only annotation**: `null` plus nested comment.
- **Unknown annotation type**: content unless a rule matches.
- **Multiple attachments**: use the first attachment that has annotations.
- **Images/ink annotations**: skipped in v1.
- **Empty annotation set**: produce an empty page (or a clear warning), no
  blocks.
- **Manual edits in an existing page**: lost; the page is overwritten.

## Optional Logseq properties

If `include_properties = true`, prepend:

```
citationKey:: <citationKey>
zotero-item:: <itemKey>
```

No blank line after the properties. Default is `false`.

## Determinism

For the same input and rules, the output must be byte-identical. Do not add
timestamps or import dates. The writer uses an atomic replace and always
overwrites the target file when content changed.

## Python API

```python
from zotero_hmd_export.render import render_item
from zotero_hmd_export.rules import (
    parse_background_config,
    parse_collapse_rules,
    parse_format_rules,
    parse_source_config,
    parse_tag_config,
    parse_tree_rules,
)

markdown = render_item(
    item,
    include_properties=False,
    tree_rules=parse_tree_rules(
        {"level1": "h,Yellow", "rank1": "u,Red"}
    ),
    format_rules=parse_format_rules(
        {"h,Yellow": "h2", "u,Red": "normal"}
    ),
    collapse_rules=parse_collapse_rules(
        {"default": True, "#keep-open": False}
    ),
    source=parse_source_config(
        {
            "scope": "all",
            "when": "page_change",
            "placement": "next_line",
            "page_label": "p. {page}",
        }
    ),
    tags=parse_tag_config({"default": True, "hide": ["bold"]}),
    background=parse_background_config(
        {"mode": "level", "palette": ["yellow", "red", "green"]}
    ),
)
```

- The renderer is pure: no I/O, no network, no template engine.
- It sorts annotations by `sort_index`.
- `tree_rules`, `format_rules`, `collapse_rules`, `source`, `tags`, and
  `background` are optional. Omitting them disables that output.
- `tree_rules` may mix absolute `levelN` and relative `rankN` rules. Use
  `resolve_tree_rule` to inspect the winning rule; its `level` or `rank`
  attribute is set, not both.
- `collapse_rules` is a `CollapseRules` object with a default and predicate
  overrides. Use `resolve_collapsed` to inspect the winning state.
- `background` is a `BackgroundConfig` with `mode = "off" | "annotation" |
  "level"`. Level mode requires a palette; annotation mode maps Zotero colors
  directly.
- It returns an empty string when the item has no exportable annotations.
- Otherwise the result ends with exactly one `\n`.
- The documented rules above are the source of truth; the golden fixture
  `tests/fixtures/rendered_expected.md` is the regression baseline for the
  no-source, no-tag, no-background default.
