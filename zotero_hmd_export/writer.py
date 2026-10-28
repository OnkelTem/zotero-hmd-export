"""Write Markdown pages to a target directory."""

from __future__ import annotations

import os
import string
import tempfile
from pathlib import Path

from .books import Book


class WriterError(Exception):
    """The output filename or file write is invalid."""


_ALLOWED_FIELDS = {"author", "title", "citekey"}
_PERCENT_ENCODE = {
    "%": "%25",
    ":": "%3A",
    "?": "%3F",
    '"': "%22",
    "*": "%2A",
    "<": "%3C",
    ">": "%3E",
    "|": "%7C",
    "\\": "%5C",
    "#": "%23",
}


def format_file_name(template: str, book: Book) -> str:
    """Render a file_name template for a book.

    Literal text is kept as-is. Values substituted for placeholders are
    slash-normalized and percent-encoded. ``/`` is not a path separator here;
    callers must write the target namespace separator (e.g. ``___``) themselves.
    """
    formatter = string.Formatter()
    try:
        parsed = list(formatter.parse(template))
    except ValueError as exc:
        raise WriterError(f"Invalid file_name template: {exc}") from exc

    values: dict[str, str] = {}
    for _literal, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name not in _ALLOWED_FIELDS:
            raise WriterError(
                f"Unknown file_name placeholder {{{field_name}}}; "
                f"allowed: {', '.join(sorted(_ALLOWED_FIELDS))}."
            )
        if format_spec or conversion:
            raise WriterError(
                f"file_name placeholder {{{field_name}}} cannot use "
                "format specifiers or conversions."
            )
        raw = _field_value(book, field_name)
        if not raw.strip():
            raise WriterError(
                f"file_name uses {{{field_name}}}, but its value is empty."
            )
        values[field_name] = _encode_value(raw.strip())

    try:
        name = formatter.vformat(template, (), values)
    except (KeyError, ValueError) as exc:
        raise WriterError(f"Invalid file_name template: {exc}") from exc

    if "/" in name:
        raise WriterError(
            "file_name must not contain '/'; use the desired namespace separator "
            "(for example '___') in the template."
        )
    if "\x00" in name:
        raise WriterError("file_name contains a NUL byte.")
    if not name.strip():
        raise WriterError("file_name rendered to an empty name.")
    if not name.lower().endswith(".md"):
        name += ".md"
    return name


def target_path(output_dir: Path | str, file_name: str) -> Path:
    """Join output_dir and a validated file name."""
    directory = Path(output_dir).expanduser()
    return directory / file_name


def write_page(
    path: Path | str,
    content: str,
    *,
    on_existing: str = "overwrite",
) -> str:
    """Atomically write a page. Return 'written' or 'unchanged'."""
    target = Path(path).expanduser()
    parent = target.parent
    if not parent.is_dir():
        raise WriterError(f"Output directory does not exist: {parent}")
    if target.is_dir():
        raise WriterError(f"Output path is a directory: {target}")

    normalized = content.rstrip("\n") + "\n" if content else ""
    if target.is_file():
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError as exc:
            raise WriterError(f"Cannot read existing page {target}: {exc}") from exc
        if existing == normalized:
            return "unchanged"
        if on_existing == "error":
            raise WriterError(f"Output page already exists: {target}")

    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(normalized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
        return "written"
    except OSError as exc:
        raise WriterError(f"Cannot write page {target}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _field_value(book: Book, field_name: str) -> str:
    if field_name == "author":
        return book.author
    if field_name == "title":
        return book.title
    return book.citekey


def _encode_value(value: str) -> str:
    result: list[str] = []
    for char in value:
        if char == "/":
            result.append("-")
        else:
            result.append(_PERCENT_ENCODE.get(char, char))
    return "".join(result)
