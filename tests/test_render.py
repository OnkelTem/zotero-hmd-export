"""Tests for the hierarchical Markdown renderer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from zotero_hmd_export.models import Annotation, Attachment, Item, Tag
from zotero_hmd_export.render import render_item
from zotero_hmd_export.rules import (
    BackgroundConfig,
    CollapseRules,
    FormatRule,
    SourceConfig,
    TagConfig,
    TreeRule,
    parse_collapse_rules,
    parse_format_rules,
    parse_tree_rules,
)
from zotero_hmd_export.zotero import (
    attachment_key_from_uri,
    build_zotero_link,
    color_category,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def ann(
    *,
    key: str = "A",
    annotation_type: str = "underline",
    color: str | None = "Yellow",
    text: str = "",
    comment: str = "",
    page: str = "1",
    sort: str = "1",
    tags: tuple[str, ...] = (),
    uri: str = "zotero://x",
) -> Annotation:
    return Annotation(
        key=key,
        annotation_type=annotation_type,
        color_hex="",
        color_category=color,
        page_label=page,
        sort_index=sort,
        text=text,
        comment=comment,
        tags=tuple(Tag(tag) for tag in tags),
        desktop_uri=uri,
    )


def item_with(annotations: tuple[Annotation, ...]) -> Item:
    attachment = Attachment(
        key="ATT",
        path="",
        uri="",
        annotations=annotations,
    )
    return Item(
        title="Book",
        citation_key="Key",
        item_key="ITEM",
        library_id=1,
        attachments=(attachment,),
    )


def item_from_fixture() -> Item:
    raw = load_json("item_attachments_result.json")
    assert isinstance(raw, list)
    attachment_raw = raw[0]
    attachment_key = attachment_key_from_uri(attachment_raw.get("open")) or "BBBB2222"
    annotations: list[Annotation] = []
    for raw_annotation in attachment_raw.get("annotations") or []:
        page_label = str(raw_annotation.get("annotationPageLabel") or "")
        key = str(raw_annotation.get("key") or "")
        color_hex = str(raw_annotation.get("annotationColor") or "")
        annotations.append(
            Annotation(
                key=key,
                annotation_type=str(raw_annotation.get("annotationType") or ""),
                color_hex=color_hex,
                color_category=color_category(color_hex),
                page_label=page_label,
                sort_index=str(raw_annotation.get("annotationSortIndex") or ""),
                text=str(raw_annotation.get("annotationText") or ""),
                comment=str(raw_annotation.get("annotationComment") or ""),
                tags=tuple(
                    Tag(str(tag.get("tag")))
                    for tag in raw_annotation.get("tags") or []
                    if tag.get("tag")
                ),
                desktop_uri=build_zotero_link(attachment_key, page_label, key),
            )
        )
    attachment = Attachment(
        key=attachment_key,
        path=str(attachment_raw.get("path") or ""),
        uri=str(attachment_raw.get("open") or ""),
        annotations=tuple(annotations),
    )
    return Item(
        title="Thinking, Fast and Slow",
        citation_key="Kahneman2011Thinking",
        item_key="AAAA1111",
        library_id=1,
        attachments=(attachment,),
    )


TREE_RULES = parse_tree_rules(
    {
        "level1": "h,Yellow",
        "level2": "h,Red",
        "level3": "h,Green",
        "level4": "h,Blue",
        "level5": "h,Purple",
    }
)
FORMAT_RULES = parse_format_rules(
    {
        "h,Yellow": "h2",
        "h,Red": "h3",
        "h,Green": "h4",
        "h,Blue": "h5",
        "h,Purple": "h6",
    }
)
LEGACY_SOURCE = SourceConfig(
    scope="all",
    when="block",
    min_page_gap=0,
    link=True,
    placement="inline",
    template="— {label}",
    page_label="p. {page}",
)
LEGACY_TAGS = TagConfig(default=True)


def render(
    item: Item,
    *,
    include_properties: bool = False,
    tree_rules: tuple[TreeRule, ...] | None = None,
    format_rules: tuple[FormatRule, ...] | None = None,
    collapse_rules: CollapseRules | None = None,
    source: SourceConfig | None = LEGACY_SOURCE,
    tags: TagConfig | None = LEGACY_TAGS,
    background: BackgroundConfig | None = None,
) -> str:
    return render_item(
        item,
        include_properties=include_properties,
        tree_rules=TREE_RULES if tree_rules is None else tree_rules,
        format_rules=FORMAT_RULES if format_rules is None else format_rules,
        collapse_rules=collapse_rules,
        source=source,
        tags=tags,
        background=background,
    )


class RendererTest(unittest.TestCase):
    def test_heading_and_content_exact(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            comment="h comment",
            page="7",
            sort="1",
            uri="zotero://a",
        )
        content = ann(
            key="C",
            text="Content",
            comment="c comment",
            page="7",
            sort="2",
            tags=("tag1",),
            uri="zotero://b",
        )
        self.assertEqual(
            render(item_with((heading, content))),
            "- ## Heading — [p. 7](zotero://a)\n"
            "  - ==h comment==\n"
            "  - Content #[[tag1]] — [p. 7](zotero://b)\n"
            "    - ==c comment==\n",
        )

    def test_no_rules_render_flat_content(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            page="7",
            sort="1",
            uri="",
        )
        self.assertEqual(render_item(item_with((heading,))), "- Heading\n")

    def test_content_before_first_heading(self) -> None:
        content = ann(
            key="C",
            color="Orange",
            text="Intro",
            comment="c",
            page="1",
            sort="1",
            tags=("t",),
            uri="zotero://c",
        )
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="H",
            page="2",
            sort="2",
            uri="zotero://h",
        )
        self.assertEqual(
            render(item_with((content, heading))),
            "- Intro #[[t]] — [p. 1](zotero://c)\n"
            "  - ==c==\n"
            "- ## H — [p. 2](zotero://h)\n",
        )

    def test_unknown_color_and_underline_are_content(self) -> None:
        highlight = ann(
            key="H1",
            annotation_type="highlight",
            color="Orange",
            text="not a heading",
            page="1",
            sort="1",
        )
        underline = ann(
            key="H2",
            annotation_type="underline",
            color="Yellow",
            text="still content",
            page="1",
            sort="2",
        )
        self.assertEqual(
            render(item_with((highlight, underline))),
            "- not a heading — [p. 1](zotero://x)\n"
            "- still content — [p. 1](zotero://x)\n",
        )

    def test_empty_text_renders_null_and_keeps_level(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            comment="",
            sort="1",
            uri="zotero://h",
        )
        empty = ann(
            key="E",
            annotation_type="highlight",
            text="",
            comment="empty",
            sort="2",
            uri="zotero://e",
        )
        after = ann(key="A", text="after", sort="3", uri="zotero://a")
        self.assertEqual(
            render(item_with((heading, empty, after))),
            "- ## Heading — [p. 1](zotero://h)\n"
            "- ## null — [p. 1](zotero://e)\n"
            "  - ==empty==\n"
            "  - after — [p. 1](zotero://a)\n",
        )

    def test_multiline_text_and_comment(self) -> None:
        content = ann(
            key="C",
            color=None,
            text="a\n\nb",
            comment="c\nd",
            page="",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(item_with((content,))),
            "- a<br><br>b\n"
            "  - ==c<br>d==\n",
        )

    def test_tags_on_heading_and_content(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            tags=("h1", "h 2"),
            page="",
            sort="1",
            uri="",
        )
        content = ann(
            key="C",
            text="Content",
            tags=("c1", "c2"),
            sort="2",
            uri="",
        )
        self.assertEqual(
            render(item_with((heading, content))),
            "- ## Heading #[[h1]] #[[h 2]]\n"
            "  - Content #[[c1]] #[[c2]]\n",
        )

    def test_comment_only_annotation_uses_null(self) -> None:
        content = ann(
            key="C",
            text="",
            comment="note",
            tags=("t",),
            page="3",
            sort="1",
            uri="zotero://c",
        )
        self.assertEqual(
            render(item_with((content,))),
            "- null #[[t]] — [p. 3](zotero://c)\n"
            "  - ==note==\n",
        )

    def test_skipped_tree_levels(self) -> None:
        h2 = ann(
            key="H2",
            annotation_type="highlight",
            color="Yellow",
            text="H2",
            page="",
            sort="1",
            uri="",
        )
        h4 = ann(
            key="H4",
            annotation_type="highlight",
            color="Green",
            text="H4",
            page="",
            sort="2",
            uri="",
        )
        content = ann(key="C", text="content", sort="3", uri="")
        self.assertEqual(
            render(item_with((h2, h4, content))),
            "- ## H2\n"
            "    - #### H4\n"
            "      - content\n",
        )

    def test_custom_tree_and_format_rules(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="H",
            page="",
            sort="1",
            uri="",
        )
        content = ann(key="C", color=None, text="C", page="", sort="2", uri="")
        self.assertEqual(
            render(
                item_with((heading, content)),
                tree_rules=parse_tree_rules({"Level2": "h,Yellow"}),
                format_rules=parse_format_rules({"h,Yellow": "h3"}),
            ),
            "  - ### H\n"
            "    - C\n",
        )

    def test_relative_rank_nests_under_absolute_level(self) -> None:
        parent = ann(
            key="P",
            annotation_type="highlight",
            color="Yellow",
            text="Parent",
            sort="1",
            uri="",
        )
        first = ann(key="C1", color="Red", text="First", sort="2", uri="")
        second = ann(key="C2", color="Red", text="Second", sort="3", uri="")
        self.assertEqual(
            render(
                item_with((parent, first, second)),
                tree_rules=parse_tree_rules(
                    {"level1": "h,Yellow", "rank1": "u,Red"}
                ),
                format_rules=parse_format_rules(
                    {"h,Yellow": "h2", "u,Red": "normal"}
                ),
            ),
            "- ## Parent\n"
            "  - First\n"
            "  - Second\n",
        )

    def test_relative_only_hierarchy_with_siblings_and_parents(self) -> None:
        rules = parse_tree_rules(
            {"rank1": "u,Red", "rank2": "u,Green"}
        )
        red1 = ann(key="R1", color="Red", text="Red 1", sort="1", uri="")
        green = ann(key="G", color="Green", text="Green", sort="2", uri="")
        red2 = ann(key="R2", color="Red", text="Red 2", sort="3", uri="")
        red3 = ann(key="R3", color="Red", text="Red 3", sort="4", uri="")
        self.assertEqual(
            render(
                item_with((red1, green, red2, red3)),
                tree_rules=rules,
                format_rules=(),
            ),
            "- Red 1\n"
            "  - Green\n"
            "- Red 2\n"
            "- Red 3\n",
        )

    def test_relative_rank_gap_does_not_create_depth_gap(self) -> None:
        rules = parse_tree_rules({"rank1": "u,Red", "rank3": "u,Green"})
        red = ann(key="R", color="Red", text="Red", sort="1", uri="")
        green = ann(key="G", color="Green", text="Green", sort="2", uri="")
        self.assertEqual(
            render(item_with((red, green)), tree_rules=rules, format_rules=()),
            "- Red\n"
            "  - Green\n",
        )

    def test_first_relative_rank_starts_at_base_plus_one(self) -> None:
        rules = parse_tree_rules({"rank3": "u,Red"})
        red = ann(key="R", color="Red", text="Red", sort="1", uri="")
        self.assertEqual(
            render(item_with((red,)), tree_rules=rules, format_rules=()),
            "- Red\n",
        )

    def test_new_absolute_level_resets_relative_stack(self) -> None:
        rules = parse_tree_rules(
            {
                "level3": "h,Yellow",
                "level1": "h,Green",
                "rank1": "u,Red",
            }
        )
        yellow = ann(
            key="Y",
            annotation_type="highlight",
            color="Yellow",
            text="Yellow",
            sort="1",
            uri="",
        )
        red1 = ann(key="R1", color="Red", text="Red 1", sort="2", uri="")
        green = ann(
            key="G",
            annotation_type="highlight",
            color="Green",
            text="Green",
            sort="3",
            uri="",
        )
        red2 = ann(key="R2", color="Red", text="Red 2", sort="4", uri="")
        self.assertEqual(
            render(
                item_with((yellow, red1, green, red2)),
                tree_rules=rules,
                format_rules=(),
            ),
            "    - Yellow\n"
            "      - Red 1\n"
            "- Green\n"
            "  - Red 2\n",
        )

    def test_relative_depth_is_not_capped_at_six(self) -> None:
        colors = ("Yellow", "Red", "Green", "Blue", "Purple", "Magenta", "Orange")
        rules = parse_tree_rules(
            {f"rank{index}": f"u,{color}" for index, color in enumerate(colors, 1)}
        )
        annotations = tuple(
            ann(key=color, color=color, text=color, sort=str(index), uri="")
            for index, color in enumerate(colors, 1)
        )
        expected = "".join(
            f"{' ' * (2 * index)}- {color}\n"
            for index, color in enumerate(colors)
        )
        self.assertEqual(
            render(item_with(annotations), tree_rules=rules, format_rules=()),
            expected,
        )

    def test_relative_block_with_comment_and_content_indent(self) -> None:
        rules = parse_tree_rules({"rank1": "u,Red"})
        block = ann(
            key="R",
            color="Red",
            text="Parent",
            comment="parent comment",
            sort="1",
            uri="",
        )
        content = ann(
            key="C",
            color=None,
            text="Content",
            comment="content comment",
            sort="2",
            uri="",
        )
        self.assertEqual(
            render(item_with((block, content)), tree_rules=rules, format_rules=()),
            "- Parent\n"
            "  - ==parent comment==\n"
            "  - Content\n"
            "    - ==content comment==\n",
        )

    def test_relative_empty_text_keeps_level(self) -> None:
        rules = parse_tree_rules({"rank1": "u,Red", "rank2": "u,Green"})
        red = ann(key="R", color="Red", text="Parent", sort="1", uri="")
        empty = ann(key="E", color="Green", text="", sort="2", uri="")
        sibling = ann(key="S", color="Red", text="Sibling", sort="3", uri="")
        self.assertEqual(
            render(
                item_with((red, empty, sibling)),
                tree_rules=rules,
                format_rules=(),
            ),
            "- Parent\n"
            "  - null\n"
            "- Sibling\n",
        )

    def test_relative_format_is_independent(self) -> None:
        rules = parse_tree_rules({"rank1": "u,Red"})
        red = ann(key="R", color="Red", text="Red", sort="1", uri="")
        self.assertEqual(
            render(
                item_with((red,)),
                tree_rules=rules,
                format_rules=parse_format_rules({"u,Red": "italic"}),
            ),
            "- *Red*\n",
        )

    def test_tag_relative_rule_beats_absolute_color_rule(self) -> None:
        rules = parse_tree_rules(
            {"level3": "h,Yellow", "rank1": "h,Yellow,#deep"}
        )
        plain = ann(
            key="P",
            annotation_type="highlight",
            color="Yellow",
            text="Plain",
            sort="2",
            uri="",
        )
        tagged = ann(
            key="T",
            annotation_type="highlight",
            color="Yellow",
            text="Tagged",
            tags=("deep",),
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(item_with((tagged, plain)), tree_rules=rules, format_rules=()),
            "- Tagged #[[deep]]\n"
            "    - Plain\n",
        )

    def test_collapse_default_true_applies_to_parents_only(self) -> None:
        parent = ann(
            key="P",
            annotation_type="highlight",
            color="Yellow",
            text="Heading",
            sort="1",
            uri="",
        )
        child = ann(
            key="C",
            annotation_type="highlight",
            color="Red",
            text="Child",
            sort="2",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((parent, child)),
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- ## Heading\n"
            "  collapsed:: true\n"
            "  - ### Child\n",
        )

    def test_collapse_rule_skips_leaf_blocks(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "level2": "u,Red"})
        collapse = parse_collapse_rules({"u,Yellow": True})
        parent = ann(key="P", color="Yellow", text="Parent", sort="1", uri="")
        child = ann(key="C", color="Red", text="Child", sort="2", uri="")
        leaf = ann(key="L", color="Yellow", text="Leaf", sort="3", uri="")
        self.assertEqual(
            render(
                item_with((parent, child, leaf)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=collapse,
            ),
            "- Parent\n"
            "  collapsed:: true\n"
            "  - Child\n"
            "- Leaf\n",
        )

    def test_collapse_tag_override_keeps_block_open(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "level2": "u,Red"})
        collapse = parse_collapse_rules({"default": True, "#keep-open": False})
        parent = ann(
            key="P",
            color="Yellow",
            text="Parent",
            tags=("keep-open",),
            sort="1",
            uri="",
        )
        child = ann(key="C", color="Red", text="Child", sort="2", uri="")
        self.assertEqual(
            render(
                item_with((parent, child)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=collapse,
            ),
            "- Parent #[[keep-open]]\n"
            "  - Child\n",
        )

    def test_collapse_comment_counts_as_child(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow"})
        block = ann(
            key="B",
            color="Yellow",
            text="Text",
            comment="note",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- Text\n"
            "  collapsed:: true\n"
            "  - ==note==\n",
        )

    def test_collapse_content_before_first_block(self) -> None:
        block = ann(
            key="B",
            color=None,
            text="Intro",
            comment="note",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                tree_rules=(),
                format_rules=(),
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- Intro\n"
            "  collapsed:: true\n"
            "  - ==note==\n",
        )

    def test_collapse_property_indent_for_nested_blocks(self) -> None:
        parent = ann(
            key="P",
            annotation_type="highlight",
            color="Yellow",
            text="Parent",
            sort="1",
            uri="",
        )
        child = ann(
            key="C",
            annotation_type="highlight",
            color="Red",
            text="Child",
            sort="2",
            uri="",
        )
        grandchild = ann(
            key="G",
            annotation_type="highlight",
            color="Green",
            text="Grandchild",
            sort="3",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((parent, child, grandchild)),
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- ## Parent\n"
            "  collapsed:: true\n"
            "  - ### Child\n"
            "    collapsed:: true\n"
            "    - #### Grandchild\n",
        )

    def test_collapse_relative_hierarchy(self) -> None:
        tree = parse_tree_rules(
            {"level1": "h,Yellow", "rank1": "u,Red", "rank2": "u,Green"}
        )
        parent = ann(
            key="Y",
            annotation_type="highlight",
            color="Yellow",
            text="Yellow",
            sort="1",
            uri="",
        )
        child = ann(key="R", color="Red", text="Red", sort="2", uri="")
        grandchild = ann(key="G", color="Green", text="Green", sort="3", uri="")
        self.assertEqual(
            render(
                item_with((parent, child, grandchild)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- Yellow\n"
            "  collapsed:: true\n"
            "  - Red\n"
            "    collapsed:: true\n"
            "    - Green\n",
        )

    def test_tree_without_heading_format(self) -> None:
        block = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="Block",
            page="",
            sort="1",
            uri="",
        )
        child = ann(key="C", text="Child", page="", sort="2", uri="")
        self.assertEqual(
            render(
                item_with((block, child)),
                tree_rules=parse_tree_rules({"Level1": "h,Yellow"}),
                format_rules=parse_format_rules({"h,Yellow": "normal"}),
            ),
            "- Block\n"
            "  - Child\n",
        )

    def test_tag_format_overrides_color_format(self) -> None:
        block = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="Tagged",
            tags=("def",),
            page="",
            sort="1",
            uri="",
        )
        child = ann(key="C", text="Child", page="", sort="2", uri="")
        self.assertEqual(
            render(
                item_with((block, child)),
                format_rules=parse_format_rules(
                    {"h,Yellow": "h2", "#def": "bold"}
                ),
            ),
            "- **Tagged** #[[def]]\n"
            "  - Child\n",
        )

    def test_tag_tree_rule_changes_level_not_format(self) -> None:
        block = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="Deep",
            tags=("deep",),
            page="",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                tree_rules=parse_tree_rules(
                    {"Level1": "h,Yellow", "Level3": "#deep"}
                ),
            ),
            "    - ## Deep #[[deep]]\n",
        )

    def test_pug_format(self) -> None:
        block = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="Text",
            page="",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                format_rules=parse_format_rules(
                    {"h,Yellow": 'pug(.note#main(style="color:red"))'}
                ),
            ),
            '- <span class="note" id="main" style="color:red">Text</span>\n',
        )

    def test_h1_format_is_allowed(self) -> None:
        block = ann(
            key="H",
            annotation_type="highlight",
            color="Yellow",
            text="Text",
            page="",
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                format_rules=parse_format_rules({"h,Yellow": "h1"}),
            ),
            "- # Text\n",
        )

    def test_no_source_without_page_label(self) -> None:
        content = ann(
            key="C",
            color=None,
            text="Text",
            page="",
            sort="1",
            uri="zotero://x",
        )
        self.assertEqual(
            render(item_with((content,))),
            "- Text\n",
        )

    def test_default_render_has_no_source_or_tags(self) -> None:
        block = ann(
            key="A",
            text="Text",
            page="7",
            tags=("tag",),
            sort="1",
            uri="zotero://x",
        )
        self.assertEqual(render_item(item_with((block,))), "- Text\n")

    def test_source_inline_uses_custom_page_label(self) -> None:
        block = ann(key="A", text="Text", page="7", sort="1", uri="zotero://x")
        source = SourceConfig(
            scope="all",
            when="block",
            placement="inline",
            page_label="p. {page}",
        )
        self.assertEqual(
            render(item_with((block,)), source=source, tags=None),
            "- Text — [p. 7](zotero://x)\n",
        )

    def test_source_uses_custom_template(self) -> None:
        block = ann(key="A", text="Text", page="7", sort="1", uri="zotero://x")
        source = SourceConfig(
            scope="all",
            when="block",
            placement="inline",
            template="source: {label}",
            page_label="{page}",
        )
        self.assertEqual(
            render(item_with((block,)), source=source, tags=None),
            "- Text source: [7](zotero://x)\n",
        )

    def test_source_scope_none_disables_output(self) -> None:
        block = ann(key="A", text="Text", page="7", sort="1", uri="zotero://x")
        self.assertEqual(
            render(
                item_with((block,)),
                source=SourceConfig(scope="none"),
                tags=None,
            ),
            "- Text\n",
        )

    def test_source_next_line_sits_after_collapsed_before_comment(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "level2": "u,Red"})
        parent = ann(
            key="P",
            color="Yellow",
            text="Parent",
            comment="note",
            page="7",
            sort="1",
            uri="zotero://p",
        )
        child = ann(
            key="C",
            color="Red",
            text="Child",
            page="7",
            sort="2",
            uri="zotero://c",
        )
        source = SourceConfig(
            scope="tree",
            when="page_change",
            placement="next_line",
            page_label="p. {page}",
        )
        self.assertEqual(
            render(
                item_with((parent, child)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=parse_collapse_rules({"default": True}),
                source=source,
                tags=None,
            ),
            "- Parent\n"
            "  collapsed:: true\n"
            "  — [p. 7](zotero://p)\n"
            "  - ==note==\n"
            "  - Child\n",
        )

    def test_next_line_source_is_not_a_child_block(self) -> None:
        block = ann(
            key="A",
            text="Text",
            page="7",
            sort="1",
            uri="zotero://x",
        )
        source = SourceConfig(
            scope="all",
            when="block",
            placement="next_line",
            page_label="{page}",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                source=source,
                tags=None,
                collapse_rules=parse_collapse_rules({"default": True}),
            ),
            "- Text\n"
            "  — [7](zotero://x)\n",
        )

    def test_source_page_change_skips_repeated_pages(self) -> None:
        source = SourceConfig(
            scope="all",
            when="page_change",
            placement="inline",
            page_label="{page}",
        )
        blocks = (
            ann(key="A", text="A", page="7", sort="1", uri="zotero://a"),
            ann(key="B", text="B", page="7", sort="2", uri="zotero://b"),
            ann(key="C", text="C", page="8", sort="3", uri="zotero://c"),
            ann(key="D", text="D", page="8", sort="4", uri="zotero://d"),
        )
        self.assertEqual(
            render(item_with(blocks), source=source, tags=None),
            "- A — [7](zotero://a)\n"
            "- B\n"
            "- C — [8](zotero://c)\n"
            "- D\n",
        )

    def test_source_level_scope_excludes_rank_and_content(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "rank1": "u,Red"})
        content = ann(
            key="C",
            color=None,
            text="Intro",
            page="7",
            sort="1",
            uri="zotero://c",
        )
        level = ann(
            key="L",
            color="Yellow",
            text="Level",
            page="7",
            sort="2",
            uri="zotero://l",
        )
        rank = ann(
            key="R",
            color="Red",
            text="Rank",
            page="7",
            sort="3",
            uri="zotero://r",
        )
        source = SourceConfig(
            scope="level",
            when="block",
            placement="inline",
            page_label="{page}",
        )
        self.assertEqual(
            render(
                item_with((content, level, rank)),
                tree_rules=tree,
                format_rules=(),
                source=source,
                tags=None,
            ),
            "- Intro\n"
            "- Level — [7](zotero://l)\n"
            "  - Rank\n",
        )

    def test_source_tree_scope_includes_level_and_rank(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "rank1": "u,Red"})
        level = ann(
            key="L",
            color="Yellow",
            text="Level",
            page="7",
            sort="1",
            uri="zotero://l",
        )
        rank = ann(
            key="R",
            color="Red",
            text="Rank",
            page="7",
            sort="2",
            uri="zotero://r",
        )
        source = SourceConfig(
            scope="tree",
            when="block",
            placement="inline",
            page_label="{page}",
        )
        self.assertEqual(
            render(
                item_with((level, rank)),
                tree_rules=tree,
                format_rules=(),
                source=source,
                tags=None,
            ),
            "- Level — [7](zotero://l)\n"
            "  - Rank — [7](zotero://r)\n",
        )

    def test_source_tree_scope_skips_content_without_consuming_page(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow"})
        content = ann(
            key="C",
            color=None,
            text="Intro",
            page="7",
            sort="1",
            uri="zotero://c",
        )
        heading = ann(
            key="H",
            color="Yellow",
            text="Heading",
            page="7",
            sort="2",
            uri="zotero://h",
        )
        source = SourceConfig(
            scope="tree",
            when="page_change",
            placement="inline",
            page_label="{page}",
        )
        self.assertEqual(
            render(
                item_with((content, heading)),
                tree_rules=tree,
                format_rules=(),
                source=source,
                tags=None,
            ),
            "- Intro\n"
            "- Heading — [7](zotero://h)\n",
        )

    def test_source_min_page_gap_for_numeric_pages(self) -> None:
        source = SourceConfig(
            scope="all",
            when="page_change",
            min_page_gap=10,
            placement="inline",
            page_label="{page}",
        )
        blocks = (
            ann(key="A", text="A", page="7", sort="1", uri="zotero://a"),
            ann(key="B", text="B", page="8", sort="2", uri="zotero://b"),
            ann(key="C", text="C", page="9", sort="3", uri="zotero://c"),
            ann(key="D", text="D", page="17", sort="4", uri="zotero://d"),
            ann(key="E", text="E", page="20", sort="5", uri="zotero://e"),
        )
        self.assertEqual(
            render(item_with(blocks), source=source, tags=None),
            "- A — [7](zotero://a)\n"
            "- B\n"
            "- C\n"
            "- D — [17](zotero://d)\n"
            "- E\n",
        )

    def test_source_min_page_gap_falls_back_for_non_numeric_pages(self) -> None:
        source = SourceConfig(
            scope="all",
            when="page_change",
            min_page_gap=10,
            placement="inline",
            page_label="{page}",
        )
        blocks = (
            ann(key="A", text="A", page="iv", sort="1", uri="zotero://a"),
            ann(key="B", text="B", page="v", sort="2", uri="zotero://b"),
        )
        self.assertEqual(
            render(item_with(blocks), source=source, tags=None),
            "- A — [iv](zotero://a)\n"
            "- B — [v](zotero://b)\n",
        )

    def test_source_without_link(self) -> None:
        block = ann(key="A", text="Text", page="7", sort="1", uri="")
        source = SourceConfig(
            scope="all",
            when="block",
            link=False,
            placement="inline",
            page_label="p. {page}",
        )
        self.assertEqual(
            render(item_with((block,)), source=source, tags=None),
            "- Text — p. 7\n",
        )

    def test_source_without_uri_or_page_is_omitted(self) -> None:
        source = SourceConfig(
            scope="all",
            when="block",
            placement="inline",
            page_label="{page}",
        )
        no_uri = ann(key="A", text="No URI", page="7", sort="1", uri="")
        no_page = ann(
            key="B",
            text="No page",
            page="",
            sort="2",
            uri="zotero://b",
        )
        self.assertEqual(
            render(item_with((no_uri, no_page)), source=source, tags=None),
            "- No URI\n"
            "- No page\n",
        )

    def test_tags_default_true_with_hidden_tags(self) -> None:
        block = ann(
            key="A",
            text="Text",
            tags=("bold", "keep", "heading"),
            sort="1",
            uri="",
        )
        tags = TagConfig(default=True, hide=("bold", "heading"))
        self.assertEqual(
            render(item_with((block,)), source=None, tags=tags),
            "- Text #[[keep]]\n",
        )

    def test_tags_selected_show_list(self) -> None:
        block = ann(
            key="A",
            text="Text",
            tags=("bold", "keep"),
            sort="1",
            uri="",
        )
        tags = TagConfig(default=False, show=("keep",))
        self.assertEqual(
            render(item_with((block,)), source=None, tags=tags),
            "- Text #[[keep]]\n",
        )

    def test_hidden_tag_still_matches_format_rule(self) -> None:
        block = ann(
            key="A",
            text="Text",
            tags=("bold",),
            sort="1",
            uri="",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                format_rules=parse_format_rules({"#bold": "bold"}),
                source=None,
                tags=TagConfig(default=True, hide=("bold",)),
            ),
            "- **Text**\n",
        )

    def test_tags_come_before_inline_source(self) -> None:
        block = ann(
            key="A",
            text="Text",
            page="7",
            tags=("keep",),
            sort="1",
            uri="zotero://x",
        )
        source = SourceConfig(
            scope="all",
            when="block",
            placement="inline",
            page_label="{page}",
        )
        self.assertEqual(
            render(
                item_with((block,)),
                source=source,
                tags=TagConfig(default=True),
            ),
            "- Text #[[keep]] — [7](zotero://x)\n",
        )

    def test_background_off_adds_no_property(self) -> None:
        block = ann(key="A", color="Yellow", text="Text", sort="1", uri="")
        self.assertEqual(
            render(
                item_with((block,)),
                source=None,
                tags=None,
            ),
            "- Text\n",
        )

    def test_background_annotation_colors_all_colored_blocks(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow"})
        level = ann(
            key="L",
            color="Yellow",
            text="Level",
            sort="1",
            uri="",
        )
        content = ann(
            key="C",
            color="Red",
            text="Content",
            sort="2",
            uri="",
        )
        background = BackgroundConfig(mode="annotation")
        self.assertEqual(
            render(
                item_with((level, content)),
                tree_rules=tree,
                format_rules=(),
                source=None,
                tags=None,
                background=background,
            ),
            "- Level\n"
            "  background-color:: yellow\n"
            "  - Content\n"
            "    background-color:: red\n",
        )

    def test_background_annotation_maps_magenta_to_pink(self) -> None:
        block = ann(key="A", color="Magenta", text="Text", sort="1", uri="")
        self.assertEqual(
            render(
                item_with((block,)),
                source=None,
                tags=None,
                background=BackgroundConfig(mode="annotation"),
            ),
            "- Text\n"
            "  background-color:: pink\n",
        )

    def test_background_annotation_skips_missing_color(self) -> None:
        block = ann(key="A", color=None, text="Text", sort="1", uri="")
        self.assertEqual(
            render(
                item_with((block,)),
                source=None,
                tags=None,
                background=BackgroundConfig(mode="annotation"),
            ),
            "- Text\n",
        )

    def test_background_does_not_make_block_a_parent(self) -> None:
        block = ann(key="A", color="Yellow", text="Text", sort="1", uri="")
        self.assertEqual(
            render(
                item_with((block,)),
                source=None,
                tags=None,
                collapse_rules=parse_collapse_rules({"default": True}),
                background=BackgroundConfig(mode="annotation"),
            ),
            "- Text\n"
            "  background-color:: yellow\n",
        )

    def test_background_level_only_colors_tree_blocks(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "level2": "u,Red"})
        level1 = ann(key="L1", color="Yellow", text="Level 1", sort="1", uri="")
        content = ann(key="C", color="Green", text="Content", sort="2", uri="")
        level2 = ann(key="L2", color="Red", text="Level 2", sort="3", uri="")
        background = BackgroundConfig(mode="level", palette=("green", "blue"))
        self.assertEqual(
            render(
                item_with((level1, content, level2)),
                tree_rules=tree,
                format_rules=(),
                source=None,
                tags=None,
                background=background,
            ),
            "- Level 1\n"
            "  background-color:: green\n"
            "  - Content\n"
            "  - Level 2\n"
            "    background-color:: blue\n",
        )

    def test_background_level_uses_computed_level_for_ranks(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "rank1": "u,Red"})
        level = ann(key="L", color="Yellow", text="Level", sort="1", uri="")
        rank = ann(key="R", color="Red", text="Rank", sort="2", uri="")
        background = BackgroundConfig(mode="level", palette=("green", "blue"))
        self.assertEqual(
            render(
                item_with((level, rank)),
                tree_rules=tree,
                format_rules=(),
                source=None,
                tags=None,
                background=background,
            ),
            "- Level\n"
            "  background-color:: green\n"
            "  - Rank\n"
            "    background-color:: blue\n",
        )

    def test_background_level_cycles_palette(self) -> None:
        tree = parse_tree_rules({"level3": "u,Yellow"})
        block = ann(key="A", color="Yellow", text="Text", sort="1", uri="")
        background = BackgroundConfig(mode="level", palette=("green", "blue"))
        self.assertEqual(
            render(
                item_with((block,)),
                tree_rules=tree,
                format_rules=(),
                source=None,
                tags=None,
                background=background,
            ),
            "    - Text\n"
            "      background-color:: green\n",
        )

    def test_background_property_order_with_collapse_and_source(self) -> None:
        tree = parse_tree_rules({"level1": "u,Yellow", "level2": "u,Red"})
        parent = ann(
            key="P",
            color="Yellow",
            text="Parent",
            comment="note",
            page="7",
            sort="1",
            uri="zotero://p",
        )
        child = ann(
            key="C",
            color="Red",
            text="Child",
            page="7",
            sort="2",
            uri="zotero://c",
        )
        source = SourceConfig(
            scope="all",
            when="block",
            placement="next_line",
            page_label="{page}",
        )
        background = BackgroundConfig(mode="level", palette=("green", "blue"))
        self.assertEqual(
            render(
                item_with((parent, child)),
                tree_rules=tree,
                format_rules=(),
                collapse_rules=parse_collapse_rules({"default": True}),
                source=source,
                tags=None,
                background=background,
            ),
            "- Parent\n"
            "  collapsed:: true\n"
            "  background-color:: green\n"
            "  — [7](zotero://p)\n"
            "  - ==note==\n"
            "  - Child\n"
            "    background-color:: blue\n"
            "    — [7](zotero://c)\n",
        )

    def test_image_and_ink_are_skipped(self) -> None:
        image = ann(key="I", annotation_type="image", text="", sort="1")
        ink = ann(key="K", annotation_type="ink", text="", sort="2")
        self.assertEqual(render(item_with((image, ink))), "")

    def test_include_properties(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            page="",
            sort="1",
            uri="",
        )
        item = item_with((heading,))
        self.assertEqual(
            render(item, include_properties=True),
            "citationKey:: Key\n"
            "zotero-item:: ITEM\n"
            "- ## Heading\n",
        )
        self.assertEqual(
            render(item, include_properties=False),
            "- ## Heading\n",
        )

    def test_no_metadata(self) -> None:
        heading = ann(
            key="H",
            annotation_type="highlight",
            text="Heading",
            page="",
            sort="1",
            uri="",
        )
        self.assertEqual(render(item_with((heading,))), "- ## Heading\n")

    def test_empty_attachment(self) -> None:
        empty_attachment = Attachment(key="ATT", path="", uri="", annotations=())
        item = Item(
            title="Book",
            citation_key="Key",
            item_key="ITEM",
            library_id=1,
            attachments=(empty_attachment,),
        )
        self.assertEqual(render(item), "")
        item_without_attachments = Item(
            title="Book",
            citation_key="Key",
            item_key="ITEM",
            library_id=1,
            attachments=(),
        )
        self.assertEqual(render(item_without_attachments), "")

    def test_determinism_and_sorting(self) -> None:
        first = ann(key="A", color=None, text="first", page="", sort="1", uri="")
        second = ann(key="B", color=None, text="second", page="", sort="2", uri="")
        item = item_with((second, first))
        output = render(item)
        self.assertEqual(output, "- first\n- second\n")
        self.assertEqual(output, render(item))

    def test_real_fixture_matches_golden(self) -> None:
        expected = (FIXTURES / "rendered_expected.md").read_text(encoding="utf-8")
        self.assertEqual(
            render(item_from_fixture(), source=None, tags=None),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
