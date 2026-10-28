"""Tests for the project books file."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_hmd_export.books import (
    Book,
    BooksError,
    find_book,
    load_books,
    save_books,
)


class BooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.path = self.root / "books.toml"

    def test_missing_file(self) -> None:
        with self.assertRaises(BooksError):
            load_books(self.path)
        self.assertEqual(load_books(self.path, allow_missing=True), ())

    def test_roundtrip(self) -> None:
        books = (
            Book(
                citekey="Key1",
                library_id=1,
                author="Kahneman",
                title="Thinking, Fast and Slow",
            ),
            Book(
                citekey="Key2",
                library_id=2,
                author="",
                title="Deep Work",
                file_name="in___txt___Deep Work.md",
            ),
        )
        save_books(self.path, books)
        loaded = load_books(self.path)
        self.assertEqual(loaded, books)
        self.assertIs(find_book(loaded, "Key1"), loaded[0])
        self.assertIsNone(find_book(loaded, "Missing"))

    def test_empty_books(self) -> None:
        save_books(self.path, ())
        self.assertEqual(load_books(self.path), ())

    def test_missing_citekey(self) -> None:
        self.path.write_text(
            """
[[books]]
library_id = 1
author = "Kahneman"
title = "Book"
""".strip()
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(BooksError):
            load_books(self.path)

    def test_invalid_library_id(self) -> None:
        self.path.write_text(
            """
[[books]]
citekey = "Key"
library_id = true
""".strip()
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(BooksError):
            load_books(self.path)

    def test_empty_file_name_becomes_none(self) -> None:
        self.path.write_text(
            """
[[books]]
citekey = "Key"
file_name = ""
""".strip()
            + "\n",
            encoding="utf-8",
        )
        books = load_books(self.path)
        self.assertIsNone(books[0].file_name)


if __name__ == "__main__":
    unittest.main()
