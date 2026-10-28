"""Hierarchical list Markdown renderer."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Annotation, Item
from .rules import (
    BackgroundConfig,
    CollapseRules,
    FormatRule,
    NO_COLLAPSE,
    SourceConfig,
    TagConfig,
    TreeRule,
    ZOTERO_BACKGROUND_MAP,
    normalize_tag,
    resolve_collapsed,
    resolve_format,
    resolve_tree_rule,
)


@dataclass(slots=True)
class _LevelTracker:
    """Track absolute levels and the stack of active relative ranks."""

    base_level: int = 0
    current_level: int = 0
    relative_stack: list[tuple[int, int]] = field(default_factory=list)

    def apply(self, rule: TreeRule) -> int:
        if rule.level is not None:
            self.base_level = rule.level
            self.relative_stack.clear()
            self.current_level = rule.level
            return self.current_level

        assert rule.rank is not None
        while self.relative_stack and self.relative_stack[-1][0] >= rule.rank:
            self.relative_stack.pop()
        parent = (
            self.relative_stack[-1][1]
            if self.relative_stack
            else self.base_level
        )
        self.current_level = parent + 1
        self.relative_stack.append((rule.rank, self.current_level))
        return self.current_level


@dataclass(slots=True)
class _SourceRenderer:
    """Build source lines and track page-change state."""

    config: SourceConfig | None
    last_page: str | None = None

    def render(
        self,
        annotation: Annotation,
        is_tree_block: bool,
        is_level_block: bool,
    ) -> str | None:
        config = self.config
        if config is None or config.scope == "none":
            return None
        if config.scope == "tree" and not is_tree_block:
            return None
        if config.scope == "level" and not is_level_block:
            return None

        page = annotation.page_label.strip()
        if not page:
            return None
        if (
            config.when == "page_change"
            and self.last_page is not None
            and not _page_is_due(self.last_page, page, config.min_page_gap)
        ):
            return None

        label = config.page_label.replace("{page}", page)
        if not label:
            return None
        if config.link:
            if not annotation.desktop_uri:
                return None
            label = f"[{label}]({annotation.desktop_uri})"

        line = config.template.replace("{label}", label)
        if not line:
            return None
        self.last_page = page
        return line


def _page_is_due(last: str, current: str, min_page_gap: int) -> bool:
    if current == last:
        return False
    if min_page_gap <= 1:
        return True
    if last.isdigit() and current.isdigit():
        return abs(int(current) - int(last)) >= min_page_gap
    return True


@dataclass(slots=True)
class _RenderedBlock:
    """A rendered block before child-aware properties are added."""

    indent: int
    line: str
    comment: str
    collapsed: bool
    source_line: str = ""
    background: str = ""


def render_item(
    item: Item,
    *,
    include_properties: bool = False,
    tree_rules: tuple[TreeRule, ...] | None = None,
    format_rules: tuple[FormatRule, ...] | None = None,
    collapse_rules: CollapseRules | None = None,
    source: SourceConfig | None = None,
    tags: TagConfig | None = None,
    background: BackgroundConfig | None = None,
) -> str:
    """Render an item's annotations as list-based Markdown.

    Tree rules choose block nesting; format rules choose the visual format;
    collapse rules choose Logseq's ``collapsed`` block state; source settings
    choose page links; tag settings choose which tags are printed; background
    settings choose Logseq block colors. They are resolved independently.
    """
    attachment = item.attachment
    if attachment is None:
        return ""

    tree = tree_rules if tree_rules is not None else ()
    formats = format_rules if format_rules is not None else ()
    collapse = collapse_rules if collapse_rules is not None else NO_COLLAPSE
    source_renderer = _SourceRenderer(source)

    annotations = sorted(attachment.annotations, key=lambda annotation: annotation.sort_index)
    lines: list[str] = []

    if include_properties:
        lines.append(f"citationKey:: {item.citation_key}")
        lines.append(f"zotero-item:: {item.item_key}")

    tracker = _LevelTracker()
    blocks: list[_RenderedBlock] = []
    for annotation in annotations:
        if annotation.annotation_type.strip().lower() in {"image", "ink"}:
            continue

        rule = resolve_tree_rule(annotation, tree)
        if rule is not None:
            level = tracker.apply(rule)
            block_indent = 2 * (level - 1)
            block_level: int | None = level
        else:
            block_indent = 2 * tracker.current_level
            block_level = None

        text = _normalize(annotation.text) or "null"
        formatted = resolve_format(annotation, formats).apply(text)
        tags_suffix = _tags_suffix(annotation, tags)
        is_level_block = rule is not None and rule.level is not None
        source_line = source_renderer.render(
            annotation,
            is_tree_block=rule is not None,
            is_level_block=is_level_block,
        )
        inline_source = ""
        next_line_source = ""
        if source_line is not None:
            if source is not None and source.placement == "inline":
                inline_source = " " + source_line
            else:
                next_line_source = source_line
        blocks.append(
            _RenderedBlock(
                indent=block_indent,
                line=f"{' ' * block_indent}- {formatted}{tags_suffix}{inline_source}",
                comment=_normalize(annotation.comment),
                collapsed=resolve_collapsed(annotation, collapse),
                source_line=next_line_source,
                background=_background_color(annotation, background, block_level),
            )
        )

    for index, block in enumerate(blocks):
        lines.append(block.line)
        has_child = bool(block.comment) or (
            index + 1 < len(blocks) and blocks[index + 1].indent > block.indent
        )
        if block.collapsed and has_child:
            lines.append(f"{' ' * (block.indent + 2)}collapsed:: true")
        if block.background:
            lines.append(
                f"{' ' * (block.indent + 2)}background-color:: {block.background}"
            )
        if block.source_line:
            lines.append(f"{' ' * (block.indent + 2)}{block.source_line}")
        if block.comment:
            lines.append(f"{' ' * (block.indent + 2)}- =={block.comment}==")

    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _background_color(
    annotation: Annotation,
    config: BackgroundConfig | None,
    block_level: int | None,
) -> str:
    if config is None or config.mode == "off":
        return ""
    if config.mode == "annotation":
        color = (annotation.color_category or "").lower()
        return ZOTERO_BACKGROUND_MAP.get(color, "")
    if config.mode == "level":
        if block_level is None or not config.palette:
            return ""
        return config.palette[(block_level - 1) % len(config.palette)]
    return ""


def _normalize(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized.replace("\n", "<br>")


def _tags_suffix(annotation: Annotation, config: TagConfig | None) -> str:
    if config is None or not annotation.tags:
        return ""
    visible: list[str] = []
    for tag in annotation.tags:
        name = normalize_tag(tag.name)
        if config.default:
            if name not in config.hide:
                visible.append(tag.name)
        elif name in config.show:
            visible.append(tag.name)
    if not visible:
        return ""
    return " " + " ".join(f"#[[{name}]]" for name in visible)
