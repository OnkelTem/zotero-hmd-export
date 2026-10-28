"""Tests for predicate, tree, and format rules."""

from __future__ import annotations

import unittest

from zotero_hmd_export.models import Annotation, Tag
from zotero_hmd_export.rules import (
    RuleError,
    Format,
    NORMAL_FORMAT,
    parse_background_config,
    parse_collapse_rules,
    parse_format,
    parse_format_rules,
    parse_predicate,
    parse_source_config,
    parse_tag_config,
    parse_tree_rules,
    resolve_collapsed,
    resolve_format,
    resolve_tree_rule,
)


def ann(
    *,
    annotation_type: str = "highlight",
    color: str | None = "Yellow",
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


class PredicateTest(unittest.TestCase):
    def test_parse_all_conditions(self) -> None:
        predicate = parse_predicate("h,Yellow,#tag1,#tag2")
        self.assertEqual(predicate.annotation_type, "highlight")
        self.assertEqual(predicate.color, "Yellow")
        self.assertEqual(predicate.tags, ("tag1", "tag2"))
        self.assertTrue(predicate.matches(ann(tags=("tag1", "tag2"))))
        self.assertFalse(predicate.matches(ann(tags=("tag1",))))

    def test_type_aliases_and_color_case(self) -> None:
        predicate = parse_predicate("underline,red")
        self.assertEqual(predicate.annotation_type, "underline")
        self.assertEqual(predicate.color, "Red")
        self.assertTrue(predicate.matches(ann(annotation_type="underline", color="Red")))
        self.assertEqual(
            parse_predicate("highlight").annotation_type,
            "highlight",
        )

    def test_tag_hash_is_normalized(self) -> None:
        predicate = parse_predicate("#def")
        self.assertTrue(predicate.matches(ann(tags=("def",))))
        self.assertTrue(predicate.matches(ann(tags=("#def",))))

    def test_invalid_predicates(self) -> None:
        for value in (
            "",
            "h,Chartreuse",
            "h,u",
            "Red,Blue",
            "#",
            "n",
            "note",
            "image",
            "ink",
        ):
            with self.subTest(value=value):
                with self.assertRaises(RuleError):
                    parse_predicate(value)


class FormatTest(unittest.TestCase):
    def test_markdown_formats(self) -> None:
        cases = {
            "normal": "text",
            "bold": "**text**",
            "italic": "*text*",
            "bold_italic": "***text***",
            "strikethrough": "~~text~~",
            "code": "`text`",
            "underline": "<u>text</u>",
            "h1": "# text",
            "h6": "###### text",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_format(value).apply("text"), expected)

    def test_pug_style_only(self) -> None:
        self.assertEqual(
            parse_format('pug(style="color:blue")').apply("text"),
            '<span style="color:blue">text</span>',
        )

    def test_pug_class_id_and_style(self) -> None:
        self.assertEqual(
            parse_format('pug(.note#main(style="color:red"))').apply("text"),
            '<span class="note" id="main" style="color:red">text</span>',
        )

    def test_pug_span_prefix_and_escaping(self) -> None:
        self.assertEqual(
            parse_format("pug(span.note)").apply('a<br><b>'),
            '<span class="note">a<br>&lt;b&gt;</span>',
        )

    def test_invalid_formats(self) -> None:
        values = ("", "h0", "h7", "##", "pug()", "pug(.note(style")
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(RuleError):
                    parse_format(value)


class ResolveTest(unittest.TestCase):
    def test_tag_rule_beats_color_rule(self) -> None:
        rules = parse_format_rules({"h,Yellow": "h2", "#def": "bold"})
        resolved = resolve_format(ann(tags=("def",)), rules)
        self.assertEqual(resolved.style, "bold")

    def test_more_conditions_win_without_tags(self) -> None:
        rules = parse_format_rules({"h,Yellow": "h2", "Yellow": "bold"})
        self.assertEqual(resolve_format(ann(), rules).heading_level, 2)

    def test_last_matching_tag_wins_on_tie(self) -> None:
        rules = parse_tree_rules({"level1": "#a", "level2": "#b"})
        self.assertEqual(resolve_tree_rule(ann(tags=("a", "b")), rules).level, 2)
        self.assertEqual(resolve_tree_rule(ann(tags=("b", "a")), rules).level, 1)

    def test_relative_rule_resolves_by_rank(self) -> None:
        rules = parse_tree_rules({"rank1": "h,Red", "rank2": "h,Green"})
        self.assertEqual(resolve_tree_rule(ann(color="Red"), rules).rank, 1)
        self.assertEqual(resolve_tree_rule(ann(color="Green"), rules).rank, 2)

    def test_tag_relative_rule_beats_absolute_color_rule(self) -> None:
        rules = parse_tree_rules(
            {"level1": "h,Yellow", "rank1": "h,Yellow,#deep"}
        )
        resolved = resolve_tree_rule(ann(tags=("deep",)), rules)
        self.assertEqual(resolved.rank, 1)
        resolved = resolve_tree_rule(ann(), rules)
        self.assertEqual(resolved.level, 1)

    def test_no_match_returns_content(self) -> None:
        self.assertIsNone(resolve_tree_rule(ann(), ()))
        self.assertEqual(resolve_format(ann(), ()), NORMAL_FORMAT)

    def test_normal_format_is_noop(self) -> None:
        self.assertEqual(Format().apply("text"), "text")


class CollapseRulesTest(unittest.TestCase):
    def test_missing_table_uses_false_default(self) -> None:
        rules = parse_collapse_rules({})
        self.assertFalse(rules.default)
        self.assertEqual(rules.rules, ())
        self.assertFalse(resolve_collapsed(ann(), rules))

    def test_default_and_predicate_overrides(self) -> None:
        rules = parse_collapse_rules({"default": True, "h,Yellow": False})
        self.assertTrue(rules.default)
        self.assertFalse(resolve_collapsed(ann(), rules))
        self.assertTrue(resolve_collapsed(ann(color="Blue"), rules))

    def test_tag_rule_beats_color_rule(self) -> None:
        rules = parse_collapse_rules({"h,Yellow": True, "#keep": False})
        self.assertFalse(resolve_collapsed(ann(tags=("keep",)), rules))
        self.assertTrue(resolve_collapsed(ann(), rules))

    def test_more_conditions_win(self) -> None:
        rules = parse_collapse_rules({"Yellow": True, "h,Yellow": False})
        self.assertFalse(resolve_collapsed(ann(), rules))

    def test_latest_matching_tag_wins_on_tie(self) -> None:
        rules = parse_collapse_rules({"#a": False, "#b": True})
        self.assertTrue(resolve_collapsed(ann(tags=("a", "b")), rules))
        self.assertFalse(resolve_collapsed(ann(tags=("b", "a")), rules))

    def test_duplicate_collapse_predicate(self) -> None:
        with self.assertRaises(RuleError):
            parse_collapse_rules({"h,Yellow": True, "Yellow,h": False})

    def test_invalid_collapse_values(self) -> None:
        for data in (
            {"default": "true"},
            {"h,Yellow": "true"},
            {"h,Yellow": 1},
        ):
            with self.subTest(data=data):
                with self.assertRaises(RuleError):
                    parse_collapse_rules(data)  # type: ignore[arg-type]

    def test_invalid_collapse_predicate(self) -> None:
        with self.assertRaises(RuleError):
            parse_collapse_rules({"Chartreuse": True})


class SourceConfigTest(unittest.TestCase):
    def test_defaults_disable_source(self) -> None:
        config = parse_source_config({})
        self.assertEqual(config.scope, "none")
        self.assertEqual(config.when, "page_change")
        self.assertEqual(config.min_page_gap, 0)
        self.assertTrue(config.link)
        self.assertEqual(config.placement, "next_line")
        self.assertEqual(config.template, "— {label}")
        self.assertEqual(config.page_label, "{page}")

    def test_full_source_config_is_normalized(self) -> None:
        config = parse_source_config(
            {
                "scope": "TREE",
                "when": "BLOCK",
                "min_page_gap": 10,
                "link": False,
                "placement": "INLINE",
                "template": "page {label}",
                "page_label": "p. {page}",
            }
        )
        self.assertEqual(config.scope, "tree")
        self.assertEqual(config.when, "block")
        self.assertEqual(config.min_page_gap, 10)
        self.assertFalse(config.link)
        self.assertEqual(config.placement, "inline")
        self.assertEqual(config.template, "page {label}")
        self.assertEqual(config.page_label, "p. {page}")

    def test_level_scope_is_valid(self) -> None:
        config = parse_source_config({"scope": "level"})
        self.assertEqual(config.scope, "level")

    def test_invalid_source_values(self) -> None:
        for data in (
            {"scope": "some"},
            {"when": "always"},
            {"placement": "child"},
            {"min_page_gap": -1},
            {"min_page_gap": 1.5},
            {"min_page_gap": True},
            {"link": "yes"},
            {"template": 1},
            {"template": "— {url}"},
            {"page_label": "{label}"},
            {"template": "— {label"},
            {"template": "— {label}\nnext"},
            {"unknown": 1},
        ):
            with self.subTest(data=data):
                with self.assertRaises(RuleError):
                    parse_source_config(data)  # type: ignore[arg-type]


class TagConfigTest(unittest.TestCase):
    def test_empty_tags_config_emits_nothing(self) -> None:
        config = parse_tag_config({})
        self.assertFalse(config.default)
        self.assertEqual(config.hide, ())
        self.assertEqual(config.show, ())

    def test_hide_and_show_are_normalized(self) -> None:
        hidden = parse_tag_config({"default": True, "hide": ["#bold", "heading"]})
        self.assertTrue(hidden.default)
        self.assertEqual(hidden.hide, ("bold", "heading"))
        shown = parse_tag_config({"default": False, "show": ["#important"]})
        self.assertFalse(shown.default)
        self.assertEqual(shown.show, ("important",))

    def test_invalid_tag_configs(self) -> None:
        for data in (
            {"default": "true"},
            {"default": True, "show": ["important"]},
            {"default": False, "hide": ["bold"]},
            {"hide": "bold"},
            {"show": [1]},
            {"hide": ["#"]},
            {"hide": ["bold", "#bold"]},
            {"unknown": []},
        ):
            with self.subTest(data=data):
                with self.assertRaises(RuleError):
                    parse_tag_config(data)  # type: ignore[arg-type]


class BackgroundConfigTest(unittest.TestCase):
    def test_default_is_off(self) -> None:
        config = parse_background_config({})
        self.assertEqual(config.mode, "off")
        self.assertEqual(config.palette, ())

    def test_annotation_mode_needs_no_palette(self) -> None:
        config = parse_background_config({"mode": "ANNOTATION"})
        self.assertEqual(config.mode, "annotation")
        self.assertEqual(config.palette, ())

    def test_level_mode_requires_palette(self) -> None:
        with self.assertRaises(RuleError):
            parse_background_config({"mode": "level"})
        config = parse_background_config(
            {"mode": "LEVEL", "palette": ["Yellow", "Red"]}
        )
        self.assertEqual(config.mode, "level")
        self.assertEqual(config.palette, ("yellow", "red"))

    def test_invalid_background_configs(self) -> None:
        for data in (
            {"mode": "some"},
            {"palette": "yellow"},
            {"palette": [1]},
            {"palette": [""]},
            {"palette": ["chartreuse"]},
            {"unknown": 1},
        ):
            with self.subTest(data=data):
                with self.assertRaises(RuleError):
                    parse_background_config(data)  # type: ignore[arg-type]


class ParseTableTest(unittest.TestCase):
    def test_parse_tree_rules(self) -> None:
        rules = parse_tree_rules({"level1": "h,Yellow", "level3": "#tag"})
        self.assertEqual([rule.level for rule in rules], [1, 3])

    def test_parse_absolute_and_relative_rules_together(self) -> None:
        rules = parse_tree_rules(
            {"level1": "h,Yellow", "rank1": "u,Red", "rank2": "u,Green"}
        )
        self.assertEqual([rule.level for rule in rules], [1, None, None])
        self.assertEqual([rule.rank for rule in rules], [None, 1, 2])

    def test_high_rank_is_accepted(self) -> None:
        rules = parse_tree_rules({"rank99": "u,Red"})
        self.assertEqual(rules[0].rank, 99)

    def test_invalid_tree_keys_and_values(self) -> None:
        for data in (
            {"level7": "h,Yellow"},
            {"One": "h,Yellow"},
            {"rank0": "h,Yellow"},
            {"rank": "h,Yellow"},
            {"rank-1": "h,Yellow"},
            {"rank01": "h,Yellow"},
            {"level1": 2},
        ):
            with self.subTest(data=data):
                with self.assertRaises(RuleError):
                    parse_tree_rules(data)  # type: ignore[arg-type]

    def test_duplicate_tree_level(self) -> None:
        with self.assertRaises(RuleError):
            parse_tree_rules({"Level1": "h,Yellow", "level1": "h,Red"})

    def test_duplicate_tree_rank(self) -> None:
        with self.assertRaises(RuleError):
            parse_tree_rules({"Rank1": "h,Yellow", "rank1": "h,Red"})

    def test_duplicate_predicate_across_absolute_and_relative(self) -> None:
        with self.assertRaises(RuleError):
            parse_tree_rules({"level1": "h,Red", "rank1": "h,Red"})

    def test_invalid_format_value_in_table(self) -> None:
        with self.assertRaises(RuleError):
            parse_format_rules({"h,Yellow": "##"})
        with self.assertRaises(RuleError):
            parse_format_rules({"h,Yellow": 2})  # type: ignore[dict-item]


if __name__ == "__main__":
    unittest.main()
