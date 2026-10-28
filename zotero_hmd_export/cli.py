"""Command-line interface for zotero-hmd-export."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .books import Book, BooksError, find_book, load_books, save_books
from .config import (
    DEFAULT_BOOKS_NAME,
    PROJECT_CONFIG_NAME,
    ConfigError,
    load_config,
    write_project_config,
)
from .render import render_item
from .writer import WriterError, format_file_name, target_path, write_page
from .zotero import (
    BBTClient,
    ItemRef,
    ZoteroError,
    ZoteroNoAnnotationsError,
)

INIT_FILE_NAME = "book___{author}___{title}.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zotero-hmd-export",
        description=(
            "Export Zotero PDF annotations as hierarchical, list-based Markdown "
            "to a project-configured output directory."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser(
        "init",
        help="Create a project config and an empty books file.",
    )
    init.add_argument("--config", help="Project config path.")
    init.add_argument("--output-dir", help="Directory where Markdown pages are written.")
    init.add_argument("--books", help="Books file path, relative to the config.")
    init.add_argument("--file-name", help="Default file_name template.")
    init.add_argument("--force", action="store_true", help="Overwrite an existing config.")

    add = subcommands.add_parser(
        "add",
        help="Add or update a book in the project books file.",
    )
    add.add_argument("--config", help="Project config path.")
    add.add_argument("--citekey", help="Citation key; omit to select in Zotero.")
    add.add_argument("--author", help="Override the author.")
    add.add_argument("--title", help="Override the title.")
    add.add_argument("--file-name", help="Per-book file_name override.")
    add.add_argument("--update", action="store_true", help="Update an existing book.")

    export = subcommands.add_parser(
        "export",
        help="Render all project books (or one book) to the output directory.",
    )
    export.add_argument("--config", help="Project config path.")
    export.add_argument("--book", help="Only process this citation key.")
    export.add_argument("--dry-run", action="store_true", help="Do not write files.")

    doctor = subcommands.add_parser(
        "doctor",
        help="Check project config, books, output directory, and Zotero/BBT.",
    )
    doctor.add_argument("--config", help="Project config path.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "init":
            return _cmd_init(args)
        if args.command == "add":
            return _cmd_add(args)
        if args.command == "export":
            return _cmd_export(args)
        if args.command == "doctor":
            return _cmd_doctor(args)
    except (ConfigError, BooksError, WriterError, ZoteroError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except EOFError:
        print("\nInput ended; aborted.", file=sys.stderr)
        return 1
    return 2


def _cmd_init(args: argparse.Namespace) -> int:
    config_path = (
        Path(args.config).expanduser()
        if args.config
        else Path.cwd() / PROJECT_CONFIG_NAME
    ).resolve()
    if config_path.exists() and not args.force:
        raise ConfigError(f"Project config already exists: {config_path}")

    output_value = (
        args.output_dir
        or input("Output directory (e.g. /path/to/logseq/graph/pages): ").strip()
    )
    if not output_value:
        raise ConfigError("output_dir is required.")
    output_dir = Path(output_value).expanduser()
    if not output_dir.is_absolute():
        output_dir = config_path.parent / output_dir
    output_dir = output_dir.resolve()
    if not output_dir.is_dir():
        raise ConfigError(f"Output directory does not exist: {output_dir}")

    books_value = args.books or input(
        f"Books file [{DEFAULT_BOOKS_NAME}]: "
    ).strip() or DEFAULT_BOOKS_NAME
    file_name = args.file_name or input(
        f"Default file_name [{INIT_FILE_NAME}]: "
    ).strip() or INIT_FILE_NAME

    write_project_config(
        config_path,
        output_dir=output_value,
        books=books_value,
        file_name=file_name,
        include_properties=False,
        on_existing="overwrite",
    )
    books_path = Path(books_value).expanduser()
    if not books_path.is_absolute():
        books_path = config_path.parent / books_path
    if not books_path.exists():
        save_books(books_path, ())

    print(f"Config: {config_path}")
    print(f"Books:  {books_path}")
    print(f"Output: {output_dir}")
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    books = load_books(config.books_path, allow_missing=True)
    client = BBTClient(port=config.bbt_port)

    if args.citekey:
        item_ref = ItemRef(citation_key=args.citekey, library_id=1)
    else:
        print("Waiting for Zotero item selection...", file=sys.stderr)
        item_ref = client.select_item()

    item = client.fetch_item(item_ref.citation_key, item_ref.library_id)
    existing = find_book(books, item.citation_key)

    if existing is not None and not args.update:
        print(f"Book already in project: {item.citation_key}")
        return 0

    author = (
        args.author
        if args.author is not None
        else (item.author if item.author else (existing.author if existing else ""))
    )
    title = (
        args.title
        if args.title is not None
        else (item.title or (existing.title if existing else ""))
    )
    file_name = (
        args.file_name
        if args.file_name is not None
        else (existing.file_name if existing else None)
    )

    book = Book(
        citekey=item.citation_key,
        library_id=item.library_id,
        author=author,
        title=title,
        file_name=file_name,
    )
    if existing is None:
        books = books + (book,)
        action = "Added"
    else:
        books = tuple(
            book if candidate.citekey == book.citekey else candidate
            for candidate in books
        )
        action = "Updated"
    save_books(config.books_path, books)

    template = book.file_name or config.file_name
    try:
        format_file_name(template, book)
    except WriterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            f"Book saved to {config.books_path}; edit it or use "
            "--author/--file-name and run 'add --update'.",
            file=sys.stderr,
        )
        return 1

    print(f"{action}: {book.citekey}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if not config.output_dir.is_dir():
        raise ConfigError(f"Output directory does not exist: {config.output_dir}")

    books = load_books(config.books_path)
    if args.book:
        books = tuple(book for book in books if book.citekey == args.book)
        if not books:
            raise BooksError(f"Book not found in project: {args.book}")
    if not books:
        raise BooksError("No books in project. Run 'zotero-hmd-export add'.")

    prepared: list[tuple[Book, Path, str]] = []
    targets: set[Path] = set()
    for book in books:
        template = book.file_name or config.file_name
        file_name = format_file_name(template, book)
        output_path = target_path(config.output_dir, file_name)
        if output_path in targets:
            raise WriterError(f"Two books map to the same output file: {output_path}")
        targets.add(output_path)
        prepared.append((book, output_path, template))

    client = BBTClient(port=config.bbt_port)
    rendered: list[tuple[Book, Path, str]] = []
    skipped: list[str] = []
    errors: list[str] = []
    for book, output_path, _template in prepared:
        try:
            item = client.fetch_item(book.citekey, book.library_id)
        except ZoteroNoAnnotationsError as exc:
            skipped.append(f"{book.citekey}: {exc}")
            continue
        except ZoteroError as exc:
            errors.append(f"{book.citekey}: {exc}")
            continue
        markdown = render_item(
            item,
            include_properties=config.include_properties,
            tree_rules=config.tree_rules,
            format_rules=config.format_rules,
            collapse_rules=config.collapse_rules,
            source=config.source,
            tags=config.tags,
            background=config.background,
        )
        if not markdown:
            skipped.append(f"{book.citekey}: no annotations")
            continue
        rendered.append((book, output_path, markdown))

    if errors:
        for message in errors:
            print(f"error: {message}", file=sys.stderr)
        return 1

    if config.on_existing == "error":
        for book, output_path, markdown in rendered:
            if not output_path.is_file():
                continue
            try:
                existing = output_path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"{book.citekey}: cannot read {output_path}: {exc}")
                continue
            normalized = markdown.rstrip("\n") + "\n"
            if existing != normalized:
                errors.append(f"{book.citekey}: output exists: {output_path}")
        if errors:
            for message in errors:
                print(f"error: {message}", file=sys.stderr)
            return 1

    if args.dry_run:
        for book, output_path, markdown in rendered:
            status = _preview_status(output_path, markdown)
            print(f"{status}: {book.citekey} -> {output_path}")
        for message in skipped:
            print(f"skip: {message}")
        if args.book and len(rendered) == 1:
            print()
            print(rendered[0][2], end="")
        return 0

    written = 0
    unchanged = 0
    write_errors: list[str] = []
    for book, output_path, markdown in rendered:
        try:
            result = write_page(
                output_path,
                markdown,
                on_existing=config.on_existing,
            )
        except WriterError as exc:
            write_errors.append(f"{book.citekey}: {exc}")
            continue
        if result == "written":
            written += 1
        else:
            unchanged += 1
        print(f"{result}: {book.citekey} -> {output_path}")

    for message in skipped:
        print(f"skip: {message}")
    for message in write_errors:
        print(f"error: {message}", file=sys.stderr)
    print(
        f"Summary: {written} written, {unchanged} unchanged, "
        f"{len(skipped)} skipped, {len(write_errors)} errors"
    )
    return 1 if write_errors else 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    ok = True

    print(f"Config: OK {config.project_path}")
    if config.output_dir.is_dir():
        print(f"Output: OK {config.output_dir}")
    else:
        print(f"Output: FAIL {config.output_dir} (directory does not exist)")
        ok = False

    try:
        books = load_books(config.books_path)
    except BooksError as exc:
        print(f"Books: FAIL {exc}")
        ok = False
        books = ()
    else:
        print(f"Books: OK {len(books)} book(s) in {config.books_path}")
        for book in books:
            template = book.file_name or config.file_name
            try:
                format_file_name(template, book)
            except WriterError as exc:
                print(f"Books: FAIL {book.citekey}: {exc}")
                ok = False

    client = BBTClient(port=config.bbt_port)
    try:
        if client.probe():
            print(f"Zotero/BBT: OK http://127.0.0.1:{config.bbt_port}")
        else:
            print("Zotero/BBT: FAIL not ready")
            ok = False
    except ZoteroError as exc:
        print(f"Zotero/BBT: FAIL {exc}")
        ok = False

    return 0 if ok else 1


def _preview_status(output_path: Path, markdown: str) -> str:
    if not output_path.is_file():
        return "would write"
    try:
        existing = output_path.read_text(encoding="utf-8")
    except OSError:
        return "would write"
    return "unchanged" if existing == markdown.rstrip("\n") + "\n" else "would write"


if __name__ == "__main__":
    raise SystemExit(main())
