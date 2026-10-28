"""Tests for page filename building and atomic writes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_hmd_export.books import Book
from zotero_hmd_export.writer import (
    WriterError,
    format_file_name,
    target_path,
    write_page,
)


class FileNameTest(unittest.TestCase):
    def book(
        self,
        *,
        author: str = "Kahneman",
        title: str = "Thinking, Fast and Slow",
        citekey: str = "Key",
    ) -> Book:
        return Book(citekey=citekey, author=author, title=title)

    def test_literal_namespace_separator_is_kept(self) -> None:
        self.assertEqual(
            format_file_name(
                "in___txt___{author}___{title}.md",
                self.book(),
            ),
            "in___txt___Kahneman___Thinking, Fast and Slow.md",
        )

    def test_literal_file_name_without_placeholders(self) -> None:
        self.assertEqual(
            format_file_name(
                "in___txt___Kahneman___Thinking, Fast and Slow.md",
                Book(citekey="Key"),
            ),
            "in___txt___Kahneman___Thinking, Fast and Slow.md",
        )

    def test_extension_is_added(self) -> None:
        self.assertEqual(
            format_file_name("{title}", self.book()),
            "Thinking, Fast and Slow.md",
        )

    def test_unused_empty_author_is_ignored(self) -> None:
        self.assertEqual(
            format_file_name("{title}.md", self.book(author="")),
            "Thinking, Fast and Slow.md",
        )

    def test_used_empty_author_fails(self) -> None:
        with self.assertRaises(WriterError):
            format_file_name("{author}.md", self.book(author=""))

    def test_unknown_placeholder_fails(self) -> None:
        with self.assertRaises(WriterError):
            format_file_name("{unknown}.md", self.book())

    def test_format_specifier_fails(self) -> None:
        with self.assertRaises(WriterError):
            format_file_name("{title:>10}.md", self.book())

    def test_literal_slash_fails(self) -> None:
        with self.assertRaises(WriterError):
            format_file_name("in/txt/{title}.md", self.book())

    def test_placeholder_slash_becomes_dash(self) -> None:
        self.assertEqual(
            format_file_name("{author}.md", self.book(author="A/B")),
            "A-B.md",
        )

    def test_percent_encoding_for_values(self) -> None:
        self.assertEqual(
            format_file_name(
                "{title}.md",
                self.book(title='C: D? "E" %'),
            ),
            "C%3A D%3F %22E%22 %25.md",
        )

    def test_unicode_is_preserved(self) -> None:
        self.assertEqual(
            format_file_name("{author}.md", self.book(author="Müller")),
            "Müller.md",
        )

    def test_literal_percent_sequence_is_not_encoded(self) -> None:
        self.assertEqual(
            format_file_name("in___txt___A%3A.md", Book(citekey="Key")),
            "in___txt___A%3A.md",
        )

    def test_target_path(self) -> None:
        path = target_path("/tmp/pages", "a.md")
        self.assertEqual(path, Path("/tmp/pages/a.md"))


class WritePageTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.page = self.root / "page.md"

    def test_write_and_read(self) -> None:
        self.assertEqual(write_page(self.page, "text"), "written")
        self.assertEqual(self.page.read_text(encoding="utf-8"), "text\n")

    def test_unchanged(self) -> None:
        write_page(self.page, "text")
        self.assertEqual(write_page(self.page, "text\n\n"), "unchanged")
        self.assertEqual(self.page.read_text(encoding="utf-8"), "text\n")

    def test_overwrite(self) -> None:
        write_page(self.page, "old")
        self.assertEqual(write_page(self.page, "new"), "written")
        self.assertEqual(self.page.read_text(encoding="utf-8"), "new\n")

    def test_on_existing_error(self) -> None:
        write_page(self.page, "old")
        with self.assertRaises(WriterError):
            write_page(self.page, "new", on_existing="error")
        self.assertEqual(self.page.read_text(encoding="utf-8"), "old\n")

    def test_on_existing_error_same_content(self) -> None:
        write_page(self.page, "old")
        self.assertEqual(
            write_page(self.page, "old", on_existing="error"),
            "unchanged",
        )

    def test_missing_parent(self) -> None:
        with self.assertRaises(WriterError):
            write_page(self.root / "missing" / "page.md", "text")


if __name__ == "__main__":
    unittest.main()
