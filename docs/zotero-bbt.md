# Zotero access through Better BibTeX JSON-RPC

The tool talks to a running Zotero 7 instance through Better BibTeX. It does not
read `zotero.sqlite`.

## Requirements

- Zotero 7 is running locally.
- Better BibTeX is installed and enabled.
- Zotero's local communication is allowed (`Allow other applications on this
  computer to communicate with Zotero`).
- The BBT JSON-RPC server is reachable at `http://127.0.0.1:<port>`, default
  `23119`.

## Endpoints

### Interactive selection: `cayw`

```
GET /better-bibtex/cayw?format=translate&translator=36a3b0b5-bad0-4a04-b79b-441c7cef77db&exportNotes=false
```

Zotero opens its item picker. The response is JSON with an `items` array. Each
item contains at least a citation key and library information. Use this when
`--citekey` is not provided.

If the user cancels or nothing is selected, stop with a clear message.

Implementation notes:

- Items may expose `citationKey` or `citekey`; the library is `libraryID`.
- `cayw?probe=true` returns the plain text `ready` when BBT is available.
- For an explicit `--citekey`, the library defaults to `1` (My Library).

### Item metadata: `item.export`

```
POST /better-bibtex/json-rpc
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "item.export",
  "params": [
    ["Kahneman2011Thinking"],
    "36a3b0b5-bad0-4a04-b79b-441c7cef77db",
    1
  ]
}
```

The `result` is a JSON **string**. Parse it, then use `items[0]`. Relevant fields:

| Field | Meaning |
|---|---|
| `title` | Item title; used for the output filename |
| `citationKey` | Better BibTeX citation key |
| `itemKey` | Zotero item key |
| `libraryID` | Library ID; needed for `item.attachments` |
| `creators` | Creator objects (`firstName`, `lastName`, `name`, `creatorType`) |
| `attachments` | Attachment metadata (`path`, `uri`, `title`, `itemType`) |

The translator UUID above is the Better BibTeX JSON translator used by the
previous Obsidian plugin.

`title` is `items[0].title`. `author` is the first creator's `lastName`, or
`name` for single-field creators. If the source has no creator, `author` is
empty. The CLI does not invent an author; a filename template that uses
`{author}` then fails until the user supplies one in `books.toml`.

Implementation notes:

- `result` is normally a JSON **string**. The old plugin also handled an array
  whose third element is that string; the client supports both.
- Attachment entries in `item.export` may have `key: null`. Derive the key from
  the storage path or from the attachment `uri`.

### Annotations: `item.attachments`

```
POST /better-bibtex/json-rpc
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "item.attachments",
  "params": ["Kahneman2011Thinking", 1]
}
```

The result is a list. Each entry has:

| Field | Meaning |
|---|---|
| `path` | Absolute PDF path, e.g. `/home/user/Zotero/storage/BBBB2222/file.pdf` |
| `open` | Zotero open URI |
| `annotations` | List of annotation objects |

Annotation fields:

| Field | Meaning |
|---|---|
| `key` | Annotation key |
| `annotationType` | `highlight`, `underline`, `note`, `image`, `ink`, etc. |
| `annotationColor` | Hex color, e.g. `#ffd400` |
| `annotationPageLabel` | Page label as shown by Zotero |
| `annotationSortIndex` | Zero-padded document-order key |
| `annotationText` | Highlighted/underlined text |
| `annotationComment` | Comment |
| `annotationPosition` | `{ pageIndex, rects }`; not required for rules-based rendering |
| `tags` | List of `{ "tag": "..." }` |
| `dateAdded`, `dateModified` | ISO timestamps |

Use the first attachment that contains annotations. Do not merge multiple PDFs in
v1.

The client sorts annotations by `annotationSortIndex` before rendering. Unknown
colors map to `None`; type and tag tree/format rules can still match, otherwise
the annotation is plain content.

## Color hex to category

| Hex | Category |
|---|---|
| `#ffd400` | Yellow |
| `#ff6666` | Red |
| `#5fb236` | Green |
| `#2ea8e5` | Blue |
| `#a28ae5` | Purple |
| `#e56eee` | Magenta |
| `#f19837` | Orange |
| `#aaaaaa` | Gray |

## Attachment key and Zotero links

The attachment key is the directory name under `storage/`:

```
/home/user/Zotero/storage/BBBB2222/Thinking, Fast and Slow.pdf
                                    ^^^^^^^^
```

It can also be derived from the last segment of the attachment `uri`.

Build links as:

```
zotero://open-pdf/library/items/<attachmentKey>?page=<pageLabel>&annotation=<annotationKey>
```

This is the same format the old Obsidian export used.

## Errors to handle

- Connection refused / timeout: Zotero is not running, BBT is not installed, or
  the port is wrong.
- JSON-RPC error `not found: <citekey>` from `item.export`, or
  `<citekey> not found` from `item.attachments`: wrong citation key.
- Empty `items`: the user canceled item selection.
- No attachments or no annotations: produce a clear message and exit non-zero.
- Malformed JSON in `result`: report the response and exit non-zero.

Errors are exposed as `ZoteroConnectionError`, `ZoteroRPCError`,
`ZoteroNoSelectionError`, and `ZoteroDataError`. The CLI maps them to non-zero
exit codes.

## Test fixture

- Citekey: `Kahneman2011Thinking`
- Library: `1`
- Item key: `AAAA1111`
- Attachment key: `BBBB2222`
- PDF: `/home/user/Zotero/storage/BBBB2222/Thinking, Fast and Slow.pdf`
- Title: `Thinking, Fast and Slow`
- Creators: not present in the fixture, so `author` is empty; use `--author` or
  edit `books.toml` for filename templates that need `{author}`.

The client tests use recorded fixtures in `tests/fixtures/`; they never touch
the network or a real Zotero library.
