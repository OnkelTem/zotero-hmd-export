"""Tests for project config loading and generation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_hmd_export.config import (
    ConfigError,
    load_config,
    write_project_config,
)
from zotero_hmd_export.models import Annotation, Tag
from zotero_hmd_export.rules import (
    NORMAL_FORMAT,
    resolve_collapsed,
    resolve_format,
    resolve_tree_rule,
)


def make_annotation(
    *,
    annotation_type: str = "highlight",
    color: str | None = "Blue",
    tags: tuple[str, ...] = (),
) -> Annotation:
    return Annotation(
        key="A",
        annotation_type=annotation_type,
        color_hex="",
        color_category=color,
        page_label="1",
        sort_index="1",
        text="text",
        comment="",
        tags=tuple(Tag(tag) for tag in tags),
        desktop_uri="",
    )


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.project_dir = self.root / "project"
        self.project_dir.mkdir()
        self.output_dir = self.project_dir / "pages"
        self.output_dir.mkdir()
        self.project = self.project_dir / "zotero-hmd-export.toml"

    def write_project(self, body: str) -> None:
        self.project.write_text(body, encoding="utf-8")

    def test_full_config_relative_paths_and_scalar_defaults(self) -> None:
        write_project_config(
            self.project,
            output_dir="pages",
            books="data/books.toml",
            file_name="in___txt___{author}___{title}.md",
        )
        config = load_config(self.project)
        self.assertEqual(config.output_dir, self.output_dir)
        self.assertEqual(config.books_path, self.project_dir / "data" / "books.toml")
        self.assertEqual(config.file_name, "in___txt___{author}___{title}.md")
        self.assertFalse(config.include_properties)
        self.assertEqual(config.on_existing, "overwrite")
        self.assertEqual(config.bbt_port, 23119)

        self.assertEqual(config.tree_rules, ())
        self.assertEqual(config.format_rules, ())
        self.assertFalse(config.collapse_rules.default)
        self.assertEqual(config.collapse_rules.rules, ())

        blue = make_annotation()
        self.assertIsNone(resolve_tree_rule(blue, config.tree_rules))
        self.assertEqual(resolve_format(blue, config.format_rules), NORMAL_FORMAT)
        self.assertFalse(resolve_collapsed(blue, config.collapse_rules))
        self.assertIsNotNone(config.source)
        assert config.source is not None
        self.assertEqual(config.source.scope, "none")
        self.assertIsNotNone(config.tags)
        assert config.tags is not None
        self.assertFalse(config.tags.default)
        self.assertIsNotNone(config.background)
        assert config.background is not None
        self.assertEqual(config.background.mode, "off")
        self.assertEqual(config.background.palette, ())

    def test_generated_config_is_self_documenting(self) -> None:
        write_project_config(
            self.project,
            output_dir="pages",
            books="books.toml",
            file_name="{title}.md",
        )
        content = self.project.read_text(encoding="utf-8")
        for section in (
            "[project]",
            "[zotero]",
            "[tree]",
            "[format]",
            "[source]",
            "[tags]",
            "[logseq.collapse]",
            "[logseq.background]",
        ):
            self.assertIn(section, content)
        self.assertNotIn(">>> project section", content)
        self.assertLess(content.index("[project]"), content.index("[zotero]"))
        self.assertIn("# bbt_port = 23119", content)
        self.assertNotIn("Default: 23119", content)
        self.assertIn("# Selector format:", content)
        self.assertIn('#   <selector> = "<format>"', content)
        self.assertIn("# Sample hierarchy", content)
        self.assertIn("# Sample heading formats", content)
        self.assertIn('# level1 = "h,Yellow"', content)
        self.assertIn('# rank1 = "u,Red"', content)
        self.assertIn('# rank2 = "u,Green"', content)
        self.assertIn('# "h,Yellow" = "h2"', content)
        self.assertIn('# "h,Red" = "h3"', content)
        self.assertIn('# "h,Purple" = "h6"', content)
        self.assertIn("# default = false", content)
        self.assertIn('# "h,Yellow" = true', content)
        self.assertIn('# "#collapse-me" = true', content)
        self.assertIn('scope = "none"', content)
        self.assertIn('# scope = "level"', content)
        self.assertIn("# min_page_gap = 10", content)
        self.assertIn('# page_label = "p. {page}"', content)
        self.assertIn('# hide = ["bold", "heading"]', content)
        self.assertIn('# show = ["important"]', content)
        self.assertIn('mode = "off"', content)
        self.assertIn('# mode = "annotation"', content)
        self.assertIn('# mode = "level"', content)
        self.assertIn(
            '# palette = ["yellow", "red", "green", "blue", '
            '"purple", "pink", "orange", "gray"]',
            content,
        )
        self.assertNotIn("--- Built-in values ---", content)
        self.assertIn('# Setting: "output_dir"', content)
        self.assertIn('output_dir = "/path/to/logseq/graph/pages"', content)
        self.assertIn('# Setting: "file_name"', content)
        self.assertIn('# Setting: "include_properties"', content)
        self.assertIn('# Setting: "on_existing"', content)
        self.assertIn('- "overwrite": replace changed pages.', content)
        self.assertIn('- "error": abort when a different page already exists.', content)
        self.assertIn("include_properties = false", content)
        self.assertIn('on_existing = "overwrite"', content)
        self.assertIn(
            "A book-specific file_name in books.toml overrides this.",
            content,
        )
        self.assertLess(
            content.index("A book-specific file_name in books.toml overrides this."),
            content.index('file_name = "{title}.md"'),
        )
        for placeholder in (
            "$OUTPUT_DIR",
            "$BOOKS",
            "$FILE_NAME",
            "$INCLUDE_PROPERTIES_VALUE",
            "$ON_EXISTING_VALUE",
        ):
            self.assertNotIn(placeholder, content)
        self.assertIn("https://pugjs.org/language/attributes.html", content)
        self.assertIn(
            "Source metadata and tag output are configured in [source] and [tags].",
            content,
        )
        self.assertNotIn("Empty annotation text", content)
        self.assertNotIn("This is the only user config", content)

    def test_minimal_project_has_no_tree_or_format_rules(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertEqual(config.file_name, "{title}.md")
        self.assertFalse(config.include_properties)
        self.assertEqual(config.on_existing, "overwrite")
        self.assertEqual(config.bbt_port, 23119)

        self.assertEqual(config.tree_rules, ())
        self.assertEqual(config.format_rules, ())
        self.assertFalse(config.collapse_rules.default)
        self.assertEqual(config.collapse_rules.rules, ())

        blue = make_annotation()
        self.assertIsNone(resolve_tree_rule(blue, config.tree_rules))
        self.assertEqual(resolve_format(blue, config.format_rules), NORMAL_FORMAT)
        self.assertFalse(resolve_collapsed(blue, config.collapse_rules))
        self.assertIsNone(config.source)
        self.assertIsNone(config.tags)
        self.assertIsNone(config.background)

    def test_project_rules_are_used(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"
file_name = "{citekey}.md"
include_properties = true
on_existing = "error"

[zotero]
bbt_port = 23121

[tree]
level1 = "h,Blue"

[format]
"h,Blue" = "bold"
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertEqual(config.file_name, "{citekey}.md")
        self.assertTrue(config.include_properties)
        self.assertEqual(config.on_existing, "error")
        self.assertEqual(config.bbt_port, 23121)

        blue = make_annotation()
        self.assertEqual(resolve_tree_rule(blue, config.tree_rules).level, 1)
        self.assertEqual(resolve_format(blue, config.format_rules).style, "bold")

    def test_relative_tree_rules_are_loaded(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[tree]
level1 = "h,Yellow"
rank1 = "u,Red"
rank2 = "u,Green"
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        yellow = make_annotation(color="Yellow")
        red = make_annotation(annotation_type="underline", color="Red")
        green = make_annotation(annotation_type="underline", color="Green")
        self.assertEqual(resolve_tree_rule(yellow, config.tree_rules).level, 1)
        self.assertEqual(resolve_tree_rule(red, config.tree_rules).rank, 1)
        self.assertEqual(resolve_tree_rule(green, config.tree_rules).rank, 2)

    def test_logseq_collapse_rules_are_loaded(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[logseq.collapse]
default = true
"h,Yellow" = false
"#keep-open" = false
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertTrue(config.collapse_rules.default)
        self.assertEqual(len(config.collapse_rules.rules), 2)
        yellow = make_annotation(color="Yellow")
        blue = make_annotation(color="Blue")
        tagged = make_annotation(color="Blue", tags=("keep-open",))
        self.assertFalse(resolve_collapsed(yellow, config.collapse_rules))
        self.assertTrue(resolve_collapsed(blue, config.collapse_rules))
        self.assertFalse(resolve_collapsed(tagged, config.collapse_rules))

    def test_source_and_tag_config_are_loaded(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[source]
scope = "tree"
when = "block"
min_page_gap = 10
link = false
placement = "inline"
template = "page {label}"
page_label = "p. {page}"

[tags]
default = true
hide = ["bold", "heading"]
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertIsNotNone(config.source)
        assert config.source is not None
        self.assertEqual(config.source.scope, "tree")
        self.assertEqual(config.source.when, "block")
        self.assertEqual(config.source.min_page_gap, 10)
        self.assertFalse(config.source.link)
        self.assertEqual(config.source.placement, "inline")
        self.assertEqual(config.source.template, "page {label}")
        self.assertEqual(config.source.page_label, "p. {page}")
        self.assertIsNotNone(config.tags)
        assert config.tags is not None
        self.assertTrue(config.tags.default)
        self.assertEqual(config.tags.hide, ("bold", "heading"))

    def test_background_config_is_loaded(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[logseq.background]
mode = "level"
palette = ["Yellow", "Red"]
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertIsNotNone(config.background)
        assert config.background is not None
        self.assertEqual(config.background.mode, "level")
        self.assertEqual(config.background.palette, ("yellow", "red"))

    def test_defaults_section_is_ignored(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[defaults]
file_name = "{citekey}.md"
include_properties = true
on_existing = "error"
""".strip()
            + "\n"
        )
        config = load_config(self.project)
        self.assertEqual(config.file_name, "{title}.md")
        self.assertFalse(config.include_properties)
        self.assertEqual(config.on_existing, "overwrite")

    def test_missing_project(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.root / "nope.toml")

    def test_missing_output_dir(self) -> None:
        self.write_project(
            """
[project]
books = "books.toml"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_on_existing(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"
on_existing = "merge"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_port(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[zotero]
bbt_port = 0
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_duplicate_tree_level_alias(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[tree]
Level1 = "h,Yellow"
level1 = "h,Red"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_tree_key(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[tree]
level7 = "h,Yellow"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_predicate(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[tree]
level1 = "h,Chartreuse"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_collapse_value(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[logseq.collapse]
"h,Yellow" = "true"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_source_value(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[source]
scope = "some"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_tags_value(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[tags]
default = false
hide = ["bold"]
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_background_value(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[logseq.background]
mode = "level"
palette = ["chartreuse"]
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_invalid_format(self) -> None:
        self.write_project(
            """
[project]
output_dir = "pages"
books = "books.toml"

[format]
"h,Yellow" = "##"
""".strip()
            + "\n"
        )
        with self.assertRaises(ConfigError):
            load_config(self.project)

    def test_write_project_config_roundtrip(self) -> None:
        path = write_project_config(
            self.project,
            output_dir=str(self.output_dir),
            books="books.toml",
            file_name="{title}.md",
            include_properties=True,
            on_existing="error",
        )
        self.assertEqual(path, self.project.resolve())
        content = self.project.read_text(encoding="utf-8")
        self.assertIn("include_properties = true", content)
        self.assertIn('on_existing = "error"', content)
        self.assertNotIn("# include_properties", content)
        self.assertNotIn("# on_existing", content)
        config = load_config(self.project)
        self.assertTrue(config.include_properties)
        self.assertEqual(config.on_existing, "error")
        self.assertIsNotNone(config.source)
        assert config.source is not None
        self.assertEqual(config.source.scope, "none")
        self.assertIsNotNone(config.tags)
        assert config.tags is not None
        self.assertFalse(config.tags.default)
        self.assertIsNotNone(config.background)
        assert config.background is not None
        self.assertEqual(config.background.mode, "off")


if __name__ == "__main__":
    unittest.main()
