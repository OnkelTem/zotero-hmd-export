"""CLI tests with mocked Zotero access and temporary projects."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from zotero_hmd_export.books import Book, load_books, save_books
from zotero_hmd_export.cli import main
from zotero_hmd_export.config import load_config, write_project_config
from zotero_hmd_export.models import Annotation, Attachment, Creator, Item
from zotero_hmd_export.render import render_item
from zotero_hmd_export.zotero import (
    ItemRef,
    ZoteroConnectionError,
    ZoteroDataError,
)

FILE_NAME = "in___txt___{author}___{title}.md"


def make_annotation(
    *,
    key: str,
    annotation_type: str,
    text: str,
    page: str = "1",
    sort: str = "1",
) -> Annotation:
    return Annotation(
        key=key,
        annotation_type=annotation_type,
        color_hex="#ffd400",
        color_category="Yellow",
        page_label=page,
        sort_index=sort,
        text=text,
        comment="",
        tags=(),
        desktop_uri=f"zotero://open-pdf/library/items/ATT?page={page}&annotation={key}",
    )


def make_item(
    *,
    citekey: str = "Key",
    title: str = "Thinking, Fast and Slow",
    author: str = "Kahneman",
    annotations: tuple[Annotation, ...] | None = None,
) -> Item:
    if annotations is None:
        annotations = (
            make_annotation(
                key="H",
                annotation_type="highlight",
                text="Heading",
                sort="1",
            ),
            make_annotation(
                key="C",
                annotation_type="underline",
                text="Content",
                sort="2",
            ),
        )
    attachment = Attachment(key="ATT", path="", uri="", annotations=annotations)
    creators = (
        (Creator(first_name="", last_name=author, name="", creator_type="author"),)
        if author
        else ()
    )
    return Item(
        title=title,
        citation_key=citekey,
        item_key="ITEM",
        library_id=1,
        attachments=(attachment,),
        creators=creators,
    )


class FakeClient:
    def __init__(self, items: dict[str, Item], *, probe: bool = True) -> None:
        self.items = items
        self.ready = probe
        self.fetch_error: Exception | None = None

    def probe(self) -> bool:
        return self.ready

    def select_item(self) -> ItemRef:
        return ItemRef(citation_key="Key", library_id=1)

    def fetch_item(self, citekey: str, library_id: int = 1) -> Item:
        if self.fetch_error is not None:
            raise self.fetch_error
        try:
            return self.items[citekey]
        except KeyError as exc:
            raise ZoteroDataError(f"no item {citekey}") from exc


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.project_dir = self.root / "project"
        self.project_dir.mkdir()
        self.pages = self.project_dir / "pages"
        self.pages.mkdir()
        self.config_path = self.project_dir / "zotero-hmd-export.toml"
        self.books_path = self.project_dir / "books.toml"
        self.xdg = self.root / "xdg"
        self.xdg.mkdir()
        self._env = patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.xdg)})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.fake = FakeClient({})

    def write_project(
        self,
        *,
        file_name: str = FILE_NAME,
        on_existing: str = "overwrite",
    ) -> None:
        write_project_config(
            self.config_path,
            output_dir=str(self.pages),
            books="books.toml",
            file_name=file_name,
            include_properties=False,
            on_existing=on_existing,
        )

    def enable_tree_and_format(self) -> None:
        content = self.config_path.read_text(encoding="utf-8")
        content = content.replace(
            "[tree]\n",
            '[tree]\nlevel1 = "h,Yellow"\n',
            1,
        ).replace(
            "[format]\n",
            '[format]\n"h,Yellow" = "h2"\n',
            1,
        )
        self.config_path.write_text(content, encoding="utf-8")

    def enable_collapse(self) -> None:
        content = self.config_path.read_text(encoding="utf-8")
        content = content.replace(
            "[logseq.collapse]\n",
            "[logseq.collapse]\ndefault = true\n",
            1,
        )
        self.config_path.write_text(content, encoding="utf-8")

    def enable_source(self) -> None:
        content = self.config_path.read_text(encoding="utf-8")
        old = (
            'scope = "none"\n'
            'when = "page_change"\n'
            "min_page_gap = 0\n"
            "link = true\n"
            'placement = "next_line"\n'
            'template = "— {label}"\n'
            'page_label = "{page}"'
        )
        new = (
            'scope = "all"\n'
            'when = "page_change"\n'
            "min_page_gap = 0\n"
            "link = true\n"
            'placement = "next_line"\n'
            'template = "— {label}"\n'
            'page_label = "p. {page}"'
        )
        content = content.replace(old, new, 1)
        self.config_path.write_text(content, encoding="utf-8")

    def enable_background_annotation(self) -> None:
        content = self.config_path.read_text(encoding="utf-8")
        content = content.replace(
            'mode = "off"',
            'mode = "annotation"',
            1,
        )
        self.config_path.write_text(content, encoding="utf-8")

    def write_books(self, books: tuple[Book, ...]) -> None:
        save_books(self.books_path, books)

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with patch("zotero_hmd_export.cli.BBTClient", return_value=self.fake):
            with redirect_stdout(out), redirect_stderr(err):
                code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_export_writes_and_is_idempotent(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        item = make_item()
        self.fake = FakeClient({"Key": item})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 0, err)
        target = self.pages / "in___txt___Kahneman___Thinking, Fast and Slow.md"
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="utf-8"), render_item(item))

        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged", out)

    def test_export_uses_book_file_name_override(self) -> None:
        self.write_project()
        self.write_books(
            (
                Book(
                    citekey="Key",
                    author="",
                    title="",
                    file_name="exact name.md",
                ),
            )
        )
        item = make_item()
        self.fake = FakeClient({"Key": item})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 0, err)
        target = self.pages / "exact name.md"
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="utf-8"), render_item(item))

    def test_export_invalid_book_aborts_without_files(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="", title="Thinking, Fast and Slow"),))
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 1)
        self.assertIn("author", err)
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_duplicate_targets_aborts(self) -> None:
        self.write_project(file_name="same.md")
        self.write_books(
            (
                Book(citekey="A", author="A", title="A"),
                Book(citekey="B", author="B", title="B"),
            )
        )
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 1)
        self.assertIn("same", err)
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_no_annotations_is_skipped(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({"Key": make_item(annotations=())})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("skip", out)
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_fetch_error_aborts_before_write(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake.fetch_error = ZoteroConnectionError("refused")
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 1)
        self.assertIn("refused", err)
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_on_existing_error(self) -> None:
        self.write_project(on_existing="error")
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({"Key": make_item()})
        target = self.pages / "in___txt___Kahneman___Thinking, Fast and Slow.md"
        target.write_text("old\n", encoding="utf-8")
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 1)
        self.assertIn("exists", err)
        self.assertEqual(target.read_text(encoding="utf-8"), "old\n")

    def test_export_dry_run_book_prints_markdown(self) -> None:
        self.write_project()
        self.enable_tree_and_format()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        item = make_item()
        self.fake = FakeClient({"Key": item})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path), "--book", "Key", "--dry-run"]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("- ## Heading", out)
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_collapsed_blocks(self) -> None:
        self.write_project()
        self.enable_tree_and_format()
        self.enable_collapse()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({"Key": make_item()})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path), "--book", "Key", "--dry-run"]
        )
        self.assertEqual(code, 0, err)
        self.assertIn(
            "- ## Heading\n"
            "  collapsed:: true\n"
            "  - Content\n",
            out,
        )
        self.assertEqual(list(self.pages.iterdir()), [])

    def test_export_source_metadata(self) -> None:
        self.write_project()
        self.enable_tree_and_format()
        self.enable_source()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({"Key": make_item()})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path), "--book", "Key", "--dry-run"]
        )
        self.assertEqual(code, 0, err)
        self.assertIn(
            "- ## Heading\n"
            "  — [p. 1](zotero://open-pdf/library/items/ATT?page=1&annotation=H)\n"
            "  - Content\n",
            out,
        )

    def test_export_background_annotation(self) -> None:
        self.write_project()
        self.enable_tree_and_format()
        self.enable_background_annotation()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({"Key": make_item()})
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path), "--book", "Key", "--dry-run"]
        )
        self.assertEqual(code, 0, err)
        self.assertIn(
            "- ## Heading\n"
            "  background-color:: yellow\n"
            "  - Content\n"
            "    background-color:: yellow\n",
            out,
        )

    def test_export_unknown_book_filter(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        code, out, err = self.run_cli(
            ["export", "--config", str(self.config_path), "--book", "Missing"]
        )
        self.assertEqual(code, 1)
        self.assertIn("Missing", err)

    def test_add_and_update(self) -> None:
        self.write_project()
        self.fake = FakeClient({"Key": make_item()})
        code, out, err = self.run_cli(
            ["add", "--config", str(self.config_path), "--citekey", "Key"]
        )
        self.assertEqual(code, 0, err)
        books = load_books(self.books_path)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].author, "Kahneman")
        self.assertEqual(books[0].title, "Thinking, Fast and Slow")

        code, out, err = self.run_cli(
            ["add", "--config", str(self.config_path), "--citekey", "Key"]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(load_books(self.books_path)), 1)

        self.fake = FakeClient({"Key": make_item(title="Thinking, Fast and Slow, second edition")})
        code, out, err = self.run_cli(
            ["add", "--config", str(self.config_path), "--citekey", "Key", "--update"]
        )
        self.assertEqual(code, 0, err)
        books = load_books(self.books_path)
        self.assertEqual(books[0].title, "Thinking, Fast and Slow, second edition")

    def test_add_without_author_fails_after_saving(self) -> None:
        self.write_project()
        self.fake = FakeClient({"Key": make_item(author="")})
        code, out, err = self.run_cli(
            ["add", "--config", str(self.config_path), "--citekey", "Key"]
        )
        self.assertEqual(code, 1)
        self.assertIn("author", err)
        books = load_books(self.books_path)
        self.assertEqual(books[0].author, "")

    def test_add_author_override(self) -> None:
        self.write_project()
        self.fake = FakeClient({"Key": make_item(author="")})
        code, out, err = self.run_cli(
            [
                "add",
                "--config",
                str(self.config_path),
                "--citekey",
                "Key",
                "--author",
                "Newport",
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(load_books(self.books_path)[0].author, "Newport")

    def test_add_file_name_override_allows_missing_author(self) -> None:
        self.write_project()
        self.fake = FakeClient({"Key": make_item(author="")})
        code, out, err = self.run_cli(
            [
                "add",
                "--config",
                str(self.config_path),
                "--citekey",
                "Key",
                "--file-name",
                "in___txt___Kahneman___Thinking, Fast and Slow.md",
            ]
        )
        self.assertEqual(code, 0, err)
        book = load_books(self.books_path)[0]
        self.assertEqual(book.file_name, "in___txt___Kahneman___Thinking, Fast and Slow.md")

    def test_add_update_preserves_manual_author(self) -> None:
        self.write_project(file_name="{title}.md")
        self.write_books(
            (Book(citekey="Key", author="Manual", title="Old title"),)
        )
        self.fake = FakeClient({"Key": make_item(author="", title="New title")})
        code, out, err = self.run_cli(
            ["add", "--config", str(self.config_path), "--citekey", "Key", "--update"]
        )
        self.assertEqual(code, 0, err)
        book = load_books(self.books_path)[0]
        self.assertEqual(book.author, "Manual")
        self.assertEqual(book.title, "New title")

    def test_init_creates_project_and_books(self) -> None:
        code, out, err = self.run_cli(
            [
                "init",
                "--config",
                str(self.config_path),
                "--output-dir",
                str(self.pages),
                "--books",
                "books.toml",
                "--file-name",
                FILE_NAME,
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(self.config_path.is_file())
        self.assertTrue(self.books_path.is_file())
        self.assertFalse(
            (self.xdg / "zotero-hmd-export" / "config.toml").exists()
        )
        content = self.config_path.read_text(encoding="utf-8")
        self.assertIn("[tree]", content)
        self.assertIn("[format]", content)
        self.assertIn("[source]", content)
        self.assertIn("[tags]", content)
        config = load_config(self.config_path)
        self.assertEqual(config.output_dir, self.pages)
        self.assertIsNotNone(config.source)
        self.assertIsNotNone(config.tags)

    def test_init_keyboard_interrupt_is_cancelled(self) -> None:
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            code, out, err = self.run_cli(
                ["init", "--config", str(self.config_path)]
            )
        self.assertEqual(code, 130)
        self.assertIn("Cancelled.", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(self.config_path.exists())
        self.assertFalse(self.books_path.exists())

    def test_init_eof_is_aborted(self) -> None:
        with patch("builtins.input", side_effect=EOFError):
            code, out, err = self.run_cli(
                ["init", "--config", str(self.config_path)]
            )
        self.assertEqual(code, 1)
        self.assertIn("Input ended; aborted.", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(self.config_path.exists())
        self.assertFalse(self.books_path.exists())

    def test_doctor_ok_and_fail(self) -> None:
        self.write_project()
        self.write_books((Book(citekey="Key", author="Kahneman", title="Thinking, Fast and Slow"),))
        self.fake = FakeClient({}, probe=True)
        code, out, err = self.run_cli(
            ["doctor", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("Config: OK", out)
        self.assertIn("Zotero/BBT: OK", out)

        self.pages.rmdir()
        code, out, err = self.run_cli(
            ["doctor", "--config", str(self.config_path)]
        )
        self.assertEqual(code, 1)
        self.assertIn("Output: FAIL", out)


if __name__ == "__main__":
    unittest.main()
