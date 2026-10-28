# zotero-hmd-export

Export Zotero PDF annotations as hierarchical, list-based Markdown into a
project-configured output directory (for example, a Logseq Markdown graph's
`pages` folder).

Status: core features are implemented. See [docs/features/](docs/features/) for
capabilities and [docs/backlog.md](docs/backlog.md) for pending non-feature work.

## Why

Zotero annotations are flat. This tool reconstructs block nesting from rules
based on annotation type, color, and tags, and applies visual formatting
separately. Projects describe which books to export, where the Markdown files
go, and how page filenames are formed.

## Requirements

- Python 3.12 or newer.
- Zotero 7 running locally.
- Better BibTeX installed and enabled in Zotero.
- A target directory for Markdown pages (for example, a Logseq MD graph's
  `pages` directory).
- No Zotero SQLite access, no Obsidian, no third-party Python dependencies.

## Install

Development environment:

```bash
make dev
source .venv/bin/activate
zotero-hmd-export --help
```

Global install with pipx:

```bash
./install.sh
```

## Quick start

Create a project directory for one book or one reading project, then run:

```bash
zotero-hmd-export init
zotero-hmd-export add
zotero-hmd-export export
```

- `init` asks for the output directory, the books file, and the filename
  template, then writes `zotero-hmd-export.toml` and the books file (default
  `books.toml`). The suggested template is `book___{author}___{title}.md`. The
  output directory must already exist. Pass `--output-dir`, `--books`, or
  `--file-name` to skip prompts, `--config` to choose the config path, and
  `--force` to overwrite an existing config.
- `add` asks Zotero for an item selection and stores its citation key, title,
  author, and library ID in `books.toml`. Subsequent runs process every book in
  the file.
- `export` fetches annotations for every book, renders Markdown, compares it to
  the existing file, and writes only changed pages.
- `doctor` checks the project config, books, output directory, and Zotero/BBT
  connection without writing anything.

## Project layout

A project is a directory with a `zotero-hmd-export.toml` file. The file named
by `[project].books` (default `books.toml`) holds the book list. The project
config is the only user config; there is no global user config. Relative paths
in `[project]` are resolved from the directory of the project config.

`output_dir` is the final directory where Markdown pages are written. The tool
does not append `pages` or infer a graph structure.

## Project config

`init` writes a complete, self-documenting `zotero-hmd-export.toml` with
English instructions and commented examples. A minimal active config looks like
this:

```toml
# zotero-hmd-export.toml
[project]
output_dir = "/path/to/logseq/graph/pages"
books = "books.toml"
file_name = "books___{author}___{title}.md"
include_properties = false
on_existing = "overwrite"

[zotero]
# bbt_port = 23119

[tree]
# level1 = "h,Yellow"
# level2 = "h,Red"

[format]
# "h,Yellow" = "h2"

[source]
scope = "none"
when = "page_change"
min_page_gap = 0
link = true
placement = "next_line"
template = "— {label}"
page_label = "{page}"

[tags]
default = false

[logseq.collapse]
# default = false

[logseq.background]
mode = "off"
```

A missing `[zotero]` section uses the default BBT port. Missing `[tree]` or
`[format]` sections mean no tree or format rules. Missing `[logseq.collapse]`,
`[logseq.background]`, `[source]`, or `[tags]` sections mean no collapse,
background, source, or tag output.

### `[project]`

- `output_dir` (required): final pages directory. It must already exist.
- `books` (default `books.toml`): path to the book list, relative to this
  config file.
- `file_name` (default `{title}.md`): filename template. A per-book
  `file_name` overrides it.
- `include_properties` (default `false`): when `true`, each page starts with
  `citationKey:: <citationKey>` and `zotero-item:: <itemKey>`.
- `on_existing` (default `"overwrite"`): `"overwrite"` replaces changed pages;
  `"error"` aborts when a different page already exists. A page with identical
  content is reported as unchanged and is not rewritten.

### `[zotero]`

`bbt_port` (default `23119`) is the port of the Better BibTeX JSON-RPC API.
Change it only when BBT uses a different port.

### `[tree]`

`[tree]` controls block nesting only. It supports absolute `level1`…`level6`
and relative `rank1`…`rankN` keys. Each value is a predicate:

- annotation type: `h`/`u` or `highlight`/`underline`;
- color: `Yellow`, `Red`, `Green`, `Blue`, `Purple`, `Magenta`, `Orange`, or
  `Gray` (case-insensitive);
- tag: `#tag`.

Conditions are joined by commas and all must match. A tag rule beats a rule
without a tag. Within the same tier, more conditions win; ties use the latest
matching tag, then later config order. If no rule matches, the annotation is
content at the current level.

```toml
[tree]
level1 = "h,Yellow"
level2 = "h,Red"
level3 = "h,Green"
level4 = "h,Blue"
level5 = "h,Purple"
rank1 = "u,Red"
rank2 = "u,Green"
```

`level1` is a top-level list item, `level2` is nested, and so on. Absolute
nesting is limited to `level6`; there is no `level7`.

`rankN` rules continue the hierarchy below the last matched absolute level, or
below level 0 when no absolute rule has matched yet. The rank number is an
ordering, not a depth: the same rank is a sibling, a higher rank is one level
deeper than the nearest lower active rank, a lower rank pops back, and a new
absolute `levelN` resets the relative stack. Gaps such as `rank1`, `rank3`,
`rank2` still produce consecutive depths, and relative depth is not capped at
six.

Duplicate tree predicates, duplicate `levelN` keys, and duplicate `rankN` keys
are config errors.

### `[format]`

`[format]` controls visual appearance only; it never changes nesting. Keys use
the same predicate syntax and priority as `[tree]`. Values are:

- `normal` — no formatting; also the fallback when no selector matches;
- `h1` … `h6` — Markdown headings;
- `bold`, `italic`, `bold_italic`, `strikethrough`, `code`, `underline`;
- `pug(...)` — wraps the text in an HTML `span`.

```toml
[format]
"h,Yellow" = "h2"
"h,Red" = "h3"
"u,Blue,#key-idea" = "bold"
"u,Green" = 'pug(.note(style="color:green"))'
```

`pug(...)` accepts classes, one id, and a single `style="..."` attribute. The
annotation text is HTML-escaped, except that `<br>` line breaks are preserved.
See the [Pug attribute reference](https://pugjs.org/language/attributes.html).

### `[source]`

`[source]` controls page references and is disabled by default.

- `scope`: `none` (no source output), `all` (every annotation is eligible),
  `level` (only annotations matched by an absolute `levelN` rule), or `tree`
  (annotations matched by any `[tree]` rule, including `rankN`).
- `when`: `block` (every eligible annotation) or `page_change` (only when the
  page differs from the last page whose source was emitted).
- `min_page_gap`: `0` means any page change; `10` requires at least 10 numeric
  pages between source lines. Non-numeric page labels use any page change.
- `link`: `true` emits a Markdown link to the Zotero PDF; `false` prints the
  label as plain text.
- `placement`: `inline` appends the source to the block line; `next_line` puts
  it on a continuation line inside the same block.
- `template` supports `{label}`; `page_label` supports `{page}`. Neither may
  contain newlines.

```toml
[source]
scope = "tree"
when = "page_change"
min_page_gap = 0
placement = "next_line"
template = "— {label}"
page_label = "p. {page}"
```

No page label means no source line. With `link = true`, a missing Zotero link
also means no source line. A `next_line` source is block content, not a child
block, and does not count as a child for `collapsed:: true`.

### `[tags]`

Tags are not emitted by default.

- `default = false` emits only tags listed in `show`.
- `default = true` emits all tags except those listed in `hide`.
- `show` with `default = true`, and `hide` with `default = false`, are config
  errors.
- Tag names may be written with or without a leading `#`; duplicate names are
  errors.

```toml
[tags]
default = true
hide = ["bold", "heading"]
```

Hidden tags still participate in tree, format, and collapse rules, and
therefore in tree-scoped source output.

### `[logseq.collapse]`

`[logseq.collapse]` controls Logseq's `collapsed:: true` block property. This
is a block property, not a text format and not a tree level.

- `default = false` collapses only blocks matched by a rule with `true`.
- `default = true` collapses every block with children unless a rule sets
  `false`.

Every other key is a predicate with the same syntax and priority as `[tree]`.
A tag rule beats a rule without a tag, so a specific `false` rule can keep a
block open when the default is `true`.

```toml
[logseq.collapse]
default = false
"h,Yellow" = true
"h,Yellow,#keep-open" = false
```

A block is collapsed only when it has a nested block or a non-empty comment.
Leaf blocks never receive the property, even when a rule matches.

### `[logseq.background]`

`[logseq.background]` controls Logseq block background colors.

- `mode = "off"` (default): no colors.
- `mode = "annotation"`: color every annotation block by its Zotero color,
  including content blocks.
- `mode = "level"`: color only `[tree]`-matched blocks by computed depth.

`palette` is required for `mode = "level"` and cycles when the depth exceeds
its length. Supported colors are `yellow`, `red`, `green`, `blue`, `purple`,
`pink`, `orange`, and `gray`. Zotero colors map as `Yellow→yellow`,
`Red→red`, `Green→green`, `Blue→blue`, `Purple→purple`, `Magenta→pink`,
`Orange→orange`, `Gray→gray`; exact Zotero hex values are not supported.

```toml
[logseq.background]
mode = "level"
palette = ["yellow", "red", "green", "blue"]
```

`background-color::` is emitted after `collapsed:: true` and before source and
comments. Comments and source lines are never colored.

## Books

```toml
# books.toml
[[books]]
citekey = "Kahneman2011Thinking"
library_id = 1
author = "Kahneman"
title = "Thinking, Fast and Slow"

[[books]]
citekey = "Newport2016DeepWork"
library_id = 1
author = "Newport"
title = "Deep Work"

[[books]]
citekey = "Kleppmann2017Designing"
library_id = 1
author = "Kleppmann"
title = "Designing Data-Intensive Applications"
file_name = "reading_notes___kleppmann.md"   # complete override
```

`file_name` on a book overrides the project template completely; templates are
not merged.

`author` and `title` are snapshots from Zotero metadata, captured by `add`.
`author` is the first creator's last name, or a single-field creator name.
`title` is the item title. If Zotero metadata changes, run `add --update` for
that book. A manually entered author is preserved when Zotero has no author.

Annotations are fetched by `citekey`, so it is always required even when the
filename template does not use `{citekey}`.

## Filename rules

- Book `file_name` overrides project `file_name`.
- If `[project].file_name` is omitted, the built-in `{title}.md` is used.
- Allowed placeholders: `{author}`, `{title}`, `{citekey}`.
- Placeholders that are used must have non-empty values; otherwise export fails
  before writing anything.
- Placeholders that are not used may be empty.
- The namespace separator is literal: write `___` yourself. The tool does not
  replace `/` with `___`.
- In substituted values, `/` becomes `-`; `: ? " * < > | \ # %` are
  percent-encoded. Spaces, non-ASCII letters, dots, commas, and parentheses are
  preserved. Literal template text is not encoded.
- `/` in the final filename is rejected.
- `.md` is appended if the rendered name does not already end with it.

Example:

```
books___{author}___{title}.md
  + author = "Kahneman", title = "Thinking, Fast and Slow"
  -> books___Kahneman___Thinking, Fast and Slow.md
```

In Logseq this page is `[[books/Kahneman/Thinking, Fast and Slow]]`.

## Commands

```bash
# Create the full project config and books file
zotero-hmd-export init

# Add a book through the Zotero picker
zotero-hmd-export add

# Add by citation key, overriding metadata
zotero-hmd-export add --citekey Kahneman2011Thinking --author "Kahneman"

# Update stored metadata for an existing book
zotero-hmd-export add --citekey Kahneman2011Thinking --update

# Export all books
zotero-hmd-export export

# Export one book, or preview without writing
zotero-hmd-export export --book Kahneman2011Thinking
zotero-hmd-export export --book Kahneman2011Thinking --dry-run

# Check project config, books, output directory, and Zotero/BBT
zotero-hmd-export doctor
```

All commands accept `--config` to point at a project config outside the current
directory. `add` also accepts `--title`, `--file-name`, and `--author`;
`export` also accepts `--dry-run`.

`add` prints a message and exits successfully when the book is already in the
project and `--update` was not given. It validates the effective filename
template after saving; an invalid template is reported together with the
command needed to fix it.

`export` validates every book and target path before fetching annotations. Any
validation, fetch, or render error aborts the run before pages are written.
Books without annotations are reported as `skip` and do not fail the run.
`--dry-run` reports `would write` or `unchanged` for each book and prints the
rendered Markdown when exactly one book is selected.

## Output format

The full project config also contains `[zotero]`, `[tree]`, `[format]`,
`[logseq.collapse]`, `[logseq.background]`, `[source]`, and `[tags]`. Each
layer is resolved independently:

- `[tree]` decides the block level;
- `[format]` decides how the block looks;
- `[logseq.collapse]` decides whether a block with children is collapsed;
- `[logseq.background]` decides whether and how blocks are colored;
- `[source]` decides whether and where source metadata is printed;
- `[tags]` decides which annotation tags are printed.

A format of `h2` produces `- ## text`; `bold` produces `- **text**`. Tree and
format rules are independent: a heading format does not create nesting, and a
tree level does not imply a heading.

Comments are nested list items wrapped in `==...==`. Visible tags are inline
`#[[tag]]` before source metadata. Empty text renders the literal `null`.
Newlines inside text and comments become `<br>`; blank lines are not emitted.
Indentation is two spaces per level.

Example config:

```toml
[tree]
level1 = "h,Yellow"
level2 = "u,Red"

[format]
"h,Yellow" = "h2"
"u,Red" = "bold"

[source]
scope = "tree"
when = "page_change"
placement = "next_line"
page_label = "p. {page}"

[tags]
default = true

[logseq.collapse]
"h,Yellow" = true
```

Example output:

```markdown
- ## Chapter 3. Attention and effort
  collapsed:: true
  — [p. 42](zotero://open-pdf/library/items/BBBB2222?page=42&annotation=HEADING1)
  - **Effort is the cost of attention.** #[[key-idea]]
    — [p. 43](zotero://open-pdf/library/items/BBBB2222?page=43&annotation=CONTENT1)
    - ==Compare with chapter 2.==
```

Full rules and examples: [docs/output-format.md](docs/output-format.md).

## Architecture

- `zotero_hmd_export/zotero.py` — Better BibTeX JSON-RPC client.
- `zotero_hmd_export/models.py` — item, creator, attachment, annotation models.
- `zotero_hmd_export/config.py` — project config, validation, init generation.
- `zotero_hmd_export/books.py` — books file loading and saving.
- `zotero_hmd_export/rules.py` — predicates, tree/format rules, collapse,
  background, source, and tag settings.
- `zotero_hmd_export/render.py` — list-based Markdown renderer.
- `zotero_hmd_export/writer.py` — filename templates and atomic page writes.
- `zotero_hmd_export/cli.py` — `init`, `add`, `export`, `doctor`.
- `zotero_hmd_export/templates/config.toml` — the self-documenting config that
  `init` writes.

Capabilities are described in [docs/features/](docs/features/); pending
non-feature work is in [docs/backlog.md](docs/backlog.md). Decisions are recorded
in [docs/adr/](docs/adr/). Output and filename details are in
[docs/output.md](docs/output.md).

## Development

```bash
make dev    # create .venv and install the package editable
make lint   # py_compile
make test   # unittest
make clean  # remove .venv and caches
```

Tests use only the standard library `unittest`, recorded synthetic fixtures in
`tests/fixtures/`, and temporary directories. They must not touch a real Zotero
library or a real output graph.

Agent definitions and skills live in the private `agents/` git submodule.
Initialize it when you have access:

```bash
git submodule update --init --recursive
```

The exporter builds and tests without the submodule. In that case local agents
and the project-local `feature-manager` skill are unavailable; use `AGENTS.md`
and the global skills as the fallback.

## Limitations

- The output directory must already exist.
- Zotero 7 and Better BibTeX must be running.
- Image, ink, and rectangle annotations are skipped in v1.
- No PDF outline parsing in v1; structure comes from `[tree]` rules.
- Absolute `[tree]` nesting is limited to `level6`; headings are limited to
  `h6`.
- Background colors are named Logseq colors, not arbitrary hex values.
- Existing pages are overwritten by default; manual edits are lost.
- A consumer such as Logseq may need the page closed or re-indexed before it
  shows an external file change.

## Troubleshooting

- `Connection refused` or `Cannot connect to Zotero`: start Zotero and verify
  that Better BibTeX is installed and enabled.
- `Project config not found`: run `zotero-hmd-export init` in the project
  directory or pass `--config`.
- `Output directory does not exist`: create the directory before `init` or
  `export`.
- `Invalid tree key`, `Unknown condition`, or `Unknown format`: check the
  `[tree]` and `[format]` predicates in the project config.
- `Duplicate tree predicate`, `Duplicate tree level`, or `Duplicate tree rank`:
  give each rule a distinct predicate and key.
- `citekey not found`: check the citation key in Zotero/BBT.
- `file_name uses {author}, but its value is empty`: add the author to
  `books.toml`, use `add --author`, or use a template that does not use
  `{author}`.
- `Two books map to the same output file`: give one of them a distinct
  `file_name`.
- `Output page already exists` with `on_existing = "error"`: change the page or
  use `on_existing = "overwrite"`.
- `tags.show requires tags.default = false` or `tags.hide requires
  tags.default = true`: fix the `[tags]` combination.
- `logseq.background.palette is required when mode = "level"`: add a palette or
  switch the mode.
