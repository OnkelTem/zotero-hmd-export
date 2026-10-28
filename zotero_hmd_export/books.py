"""Project book list handling."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


class BooksError(Exception):
    """The books file is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Book:
    citekey: str
    library_id: int = 1
    author: str = ""
    title: str = ""
    file_name: str | None = None


def load_books(path: Path | str, *, allow_missing: bool = False) -> tuple[Book, ...]:
    """Load [[books]] entries from a TOML file."""
    books_path = Path(path).expanduser()
    if not books_path.is_file():
        if allow_missing:
            return ()
        raise BooksError(f"Books file not found: {books_path}")

    try:
        with books_path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise BooksError(f"Cannot read books file {books_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise BooksError(f"Invalid TOML in books file {books_path}: {exc}") from exc

    raw_books = data.get("books", [])
    if not isinstance(raw_books, list):
        raise BooksError(f"{books_path}: [[books]] must be a list.")

    books: list[Book] = []
    for index, raw in enumerate(raw_books, start=1):
        if not isinstance(raw, dict):
            raise BooksError(f"{books_path}: book #{index} must be a table.")
        citekey = raw.get("citekey")
        if not isinstance(citekey, str) or not citekey.strip():
            raise BooksError(f"{books_path}: book #{index} has no citekey.")
        library_id = raw.get("library_id", 1)
        if not isinstance(library_id, int) or isinstance(library_id, bool) or library_id < 1:
            raise BooksError(f"{books_path}: book #{index} has invalid library_id.")
        author = raw.get("author", "")
        title = raw.get("title", "")
        file_name = raw.get("file_name")
        if not isinstance(author, str) or not isinstance(title, str):
            raise BooksError(f"{books_path}: book #{index} author/title must be strings.")
        if file_name is not None and not isinstance(file_name, str):
            raise BooksError(f"{books_path}: book #{index} file_name must be a string.")
        if isinstance(file_name, str) and not file_name.strip():
            file_name = None
        books.append(
            Book(
                citekey=citekey.strip(),
                library_id=library_id,
                author=author,
                title=title,
                file_name=file_name,
            )
        )
    return tuple(books)


def save_books(path: Path | str, books: tuple[Book, ...]) -> Path:
    """Write [[books]] entries to a TOML file."""
    books_path = Path(path).expanduser()
    books_path.parent.mkdir(parents=True, exist_ok=True)
    if not books:
        books_path.write_text(
            "# Add books with 'zotero-hmd-export add'.\n",
            encoding="utf-8",
        )
        return books_path

    rows: list[str] = []
    for book in books:
        rows.append("[[books]]")
        rows.append(f"citekey = {_toml_quote(book.citekey)}")
        rows.append(f"library_id = {book.library_id}")
        rows.append(f"author = {_toml_quote(book.author)}")
        rows.append(f"title = {_toml_quote(book.title)}")
        if book.file_name is not None:
            rows.append(f"file_name = {_toml_quote(book.file_name)}")
        rows.append("")
    books_path.write_text("\n".join(rows), encoding="utf-8")
    return books_path


def find_book(books: tuple[Book, ...], citekey: str) -> Book | None:
    """Find a book by citekey."""
    return next((book for book in books if book.citekey == citekey), None)


def _toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
