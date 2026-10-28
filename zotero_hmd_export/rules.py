"""Predicate, tree, format, collapse, background, source, and tag rules."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass

from .models import Annotation

COLOR_ORDER: tuple[str, ...] = (
    "Yellow",
    "Red",
    "Green",
    "Blue",
    "Purple",
    "Magenta",
    "Orange",
    "Gray",
)
_COLOR_BY_LOWER = {color.lower(): color for color in COLOR_ORDER}

_TYPE_ALIASES: dict[str, str] = {
    "h": "highlight",
    "highlight": "highlight",
    "u": "underline",
    "underline": "underline",
}

MARKDOWN_STYLES = frozenset(
    {
        "normal",
        "bold",
        "italic",
        "bold_italic",
        "strikethrough",
        "code",
        "underline",
    }
)

_HEADING_RE = re.compile(r"^h([1-6])$", re.IGNORECASE)
_LEVEL_KEY_RE = re.compile(r"^level([1-6])$", re.IGNORECASE)
_RANK_KEY_RE = re.compile(r"^rank([1-9][0-9]*)$", re.IGNORECASE)
_PUG_STYLE_RE = re.compile(
    r"""^\s*style\s*=\s*(?:"([^"]*)"|'([^']*)')\s*$""",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")

class RuleError(ValueError):
    """A tree, format, collapse, background, source, or tag rule is invalid."""


def normalize_tag(value: str) -> str:
    """Normalize a tag by dropping one leading ``#`` and surrounding spaces."""
    tag = value.strip()
    if tag.startswith("#"):
        tag = tag[1:].strip()
    return tag


@dataclass(frozen=True, slots=True)
class Predicate:
    """An AND-combination of annotation type, color, and tag conditions."""

    annotation_type: str | None
    color: str | None
    tags: tuple[str, ...]
    raw: str

    @property
    def condition_count(self) -> int:
        return (
            (1 if self.annotation_type is not None else 0)
            + (1 if self.color is not None else 0)
            + len(self.tags)
        )

    def matches(self, annotation: Annotation) -> bool:
        if (
            self.annotation_type is not None
            and annotation.annotation_type.strip().lower() != self.annotation_type
        ):
            return False
        if self.color is not None and annotation.color_category != self.color:
            return False
        if self.tags:
            available = {normalize_tag(tag.name) for tag in annotation.tags}
            if not all(tag in available for tag in self.tags):
                return False
        return True

    def rank(self, annotation: Annotation, order: int) -> tuple[int, int, int, int]:
        """Return a sortable specificity rank; larger wins.

        A rule with a tag always beats a rule without a tag. Within the same
        tier, more conditions win, then the latest matching tag in annotation
        order, then later config order.
        """
        last_tag = -1
        if self.tags:
            names = [normalize_tag(tag.name) for tag in annotation.tags]
            positions = [names.index(tag) for tag in self.tags if tag in names]
            if positions:
                last_tag = max(positions)
        return (1 if self.tags else 0, self.condition_count, last_tag, order)


@dataclass(frozen=True, slots=True)
class TreeRule:
    """A predicate that assigns an absolute level or a relative rank."""

    predicate: Predicate
    order: int
    level: int | None = None
    rank: int | None = None


@dataclass(frozen=True, slots=True)
class PugSpec:
    """The parsed contents of a ``pug(...)`` span selector."""

    classes: tuple[str, ...] = ()
    element_id: str | None = None
    style: str | None = None

    def wrap(self, text: str) -> str:
        attributes: list[str] = []
        if self.classes:
            value = html.escape(" ".join(self.classes), quote=True)
            attributes.append(f'class="{value}"')
        if self.element_id is not None:
            value = html.escape(self.element_id, quote=True)
            attributes.append(f'id="{value}"')
        if self.style is not None:
            value = html.escape(self.style, quote=True)
            attributes.append(f'style="{value}"')
        suffix = (" " + " ".join(attributes)) if attributes else ""
        escaped = html.escape(text).replace("&lt;br&gt;", "<br>")
        return f"<span{suffix}>{escaped}</span>"


@dataclass(frozen=True, slots=True)
class Format:
    """A visual format. Tree level is deliberately not part of this object."""

    heading_level: int | None = None
    style: str | None = None
    pug: PugSpec | None = None
    raw: str = "normal"

    def apply(self, text: str) -> str:
        if self.heading_level is not None:
            return f"{'#' * self.heading_level} {text}"
        if self.pug is not None:
            return self.pug.wrap(text)
        if self.style is None or self.style == "normal":
            return text
        if self.style == "bold":
            return f"**{text}**"
        if self.style == "italic":
            return f"*{text}*"
        if self.style == "bold_italic":
            return f"***{text}***"
        if self.style == "strikethrough":
            return f"~~{text}~~"
        if self.style == "code":
            return f"`{text}`"
        if self.style == "underline":
            return f"<u>{text}</u>"
        raise RuleError(f"Unsupported format style: {self.style!r}")


NORMAL_FORMAT = Format(style="normal", raw="normal")


@dataclass(frozen=True, slots=True)
class FormatRule:
    """A predicate that assigns a visual format."""

    format: Format
    predicate: Predicate
    order: int


@dataclass(frozen=True, slots=True)
class CollapseRule:
    """A predicate that assigns a Logseq collapsed state."""

    collapsed: bool
    predicate: Predicate
    order: int


@dataclass(frozen=True, slots=True)
class CollapseRules:
    """A default collapse state and its predicate overrides."""

    default: bool = False
    rules: tuple[CollapseRule, ...] = ()


NO_COLLAPSE = CollapseRules()

SOURCE_SCOPES = frozenset({"none", "all", "level", "tree"})
SOURCE_WHEN = frozenset({"block", "page_change"})
SOURCE_PLACEMENTS = frozenset({"inline", "next_line"})
_SOURCE_KEYS = frozenset(
    {
        "scope",
        "when",
        "min_page_gap",
        "link",
        "placement",
        "template",
        "page_label",
    }
)
_TAG_KEYS = frozenset({"default", "hide", "show"})

BACKGROUND_MODES = frozenset({"off", "annotation", "level"})
_BACKGROUND_KEYS = frozenset({"mode", "palette"})
LOGSEQ_BACKGROUND_COLORS = frozenset(
    {"yellow", "red", "green", "blue", "purple", "pink", "orange", "gray"}
)
ZOTERO_BACKGROUND_MAP: dict[str, str] = {
    "yellow": "yellow",
    "red": "red",
    "green": "green",
    "blue": "blue",
    "purple": "purple",
    "magenta": "pink",
    "orange": "orange",
    "gray": "gray",
}


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Settings for source page links and page labels."""

    scope: str = "none"
    when: str = "page_change"
    min_page_gap: int = 0
    link: bool = True
    placement: str = "next_line"
    template: str = "— {label}"
    page_label: str = "{page}"


@dataclass(frozen=True, slots=True)
class TagConfig:
    """Settings for filtering tags in the rendered output."""

    default: bool = False
    hide: tuple[str, ...] = ()
    show: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BackgroundConfig:
    """Settings for Logseq block background colors."""

    mode: str = "off"
    palette: tuple[str, ...] = ()


def parse_predicate(value: str) -> Predicate:
    """Parse ``type,color,#tag`` conditions."""
    if not isinstance(value, str) or not value.strip():
        raise RuleError("A predicate must be a non-empty string.")

    annotation_type: str | None = None
    color: str | None = None
    tags: list[str] = []

    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            raise RuleError(f"Empty condition in predicate {value!r}.")
        if token.startswith("#"):
            tag = normalize_tag(token)
            if not tag:
                raise RuleError(f"Empty tag in predicate {value!r}.")
            if tag not in tags:
                tags.append(tag)
            continue

        lowered = token.lower()
        if lowered in _TYPE_ALIASES:
            parsed_type = _TYPE_ALIASES[lowered]
            if annotation_type is not None and annotation_type != parsed_type:
                raise RuleError(
                    f"Conflicting annotation types in predicate {value!r}."
                )
            annotation_type = parsed_type
            continue

        if lowered in _COLOR_BY_LOWER:
            parsed_color = _COLOR_BY_LOWER[lowered]
            if color is not None and color != parsed_color:
                raise RuleError(f"Conflicting colors in predicate {value!r}.")
            color = parsed_color
            continue

        raise RuleError(f"Unknown condition {token!r} in predicate {value!r}.")

    if annotation_type is None and color is None and not tags:
        raise RuleError(f"Predicate {value!r} has no conditions.")
    return Predicate(annotation_type, color, tuple(tags), value.strip())


def parse_format(value: str) -> Format:
    """Parse ``normal``, ``h1``…``h6``, a Markdown style, or ``pug(...)``."""
    if not isinstance(value, str) or not value.strip():
        raise RuleError("A format must be a non-empty string.")
    raw = value.strip()
    lowered = raw.lower()

    if lowered == "normal":
        return NORMAL_FORMAT

    heading_match = _HEADING_RE.fullmatch(lowered)
    if heading_match:
        return Format(heading_level=int(heading_match.group(1)), raw=raw)

    if lowered in MARKDOWN_STYLES:
        return Format(style=lowered, raw=raw)

    if lowered.startswith("pug(") and raw.endswith(")"):
        return Format(pug=_parse_pug(raw[4:-1], raw), raw=raw)

    raise RuleError(
        f"Unknown format {raw!r}; expected normal, h1..h6, "
        f"{', '.join(sorted(MARKDOWN_STYLES - {'normal'}))}, or pug(...)."
    )


def _parse_pug(body: str, raw: str) -> PugSpec:
    if not body.strip():
        raise RuleError(f"Empty pug format {raw!r}.")
    inner = body.strip()
    if inner.lower() == "span":
        inner = ""
    elif inner.lower().startswith("span") and len(inner) > 4 and inner[4] in ".#( ":
        inner = inner[4:].strip()

    classes: list[str] = []
    element_id: str | None = None
    index = 0
    while index < len(inner) and inner[index] in ".#":
        kind = inner[index]
        index += 1
        start = index
        while index < len(inner) and (inner[index].isalnum() or inner[index] in "_-"):
            index += 1
        name = inner[start:index]
        if not name:
            raise RuleError(f"Invalid pug selector in {raw!r}.")
        if kind == ".":
            classes.append(name)
        else:
            if element_id is not None:
                raise RuleError(f"Multiple ids in pug selector {raw!r}.")
            element_id = name

    rest = inner[index:].strip()
    style: str | None = None
    if rest:
        if rest.startswith("(") and rest.endswith(")"):
            attributes = rest[1:-1].strip()
        elif rest.lower().startswith("style"):
            attributes = rest
        else:
            raise RuleError(f"Invalid pug attributes in {raw!r}.")
        if attributes:
            match = _PUG_STYLE_RE.fullmatch(attributes)
            if not match:
                raise RuleError(
                    f"Only a single style=\"...\" attribute is supported in {raw!r}."
                )
            style = match.group(1) if match.group(1) is not None else match.group(2)

    return PugSpec(classes=tuple(classes), element_id=element_id, style=style)


def _predicate_key(predicate: Predicate) -> tuple[str | None, str | None, tuple[str, ...]]:
    return (predicate.annotation_type, predicate.color, tuple(sorted(predicate.tags)))


def parse_tree_rules(data: Mapping[str, object]) -> tuple[TreeRule, ...]:
    """Parse a ``[tree]`` table into ordered absolute and relative rules."""
    rules: list[TreeRule] = []
    seen_levels: set[int] = set()
    seen_ranks: set[int] = set()
    seen_predicates: set[tuple[str | None, str | None, tuple[str, ...]]] = set()
    for order, (key, value) in enumerate(data.items()):
        key_text = str(key).strip()
        level_match = _LEVEL_KEY_RE.fullmatch(key_text)
        rank_match = _RANK_KEY_RE.fullmatch(key_text)
        if level_match is None and rank_match is None:
            raise RuleError(
                f"Invalid tree key {key!r}; expected level1..level6 or rankN."
            )
        if not isinstance(value, str):
            raise RuleError(f"tree.{key} must be a predicate string.")
        predicate = parse_predicate(value)
        predicate_key = _predicate_key(predicate)
        if predicate_key in seen_predicates:
            raise RuleError(f"Duplicate tree predicate {value!r}.")
        if level_match is not None:
            level = int(level_match.group(1))
            if level in seen_levels:
                raise RuleError(f"Duplicate tree level {level}.")
            seen_levels.add(level)
            rules.append(TreeRule(predicate=predicate, order=order, level=level))
        else:
            assert rank_match is not None
            rank = int(rank_match.group(1))
            if rank in seen_ranks:
                raise RuleError(f"Duplicate tree rank {rank}.")
            seen_ranks.add(rank)
            rules.append(TreeRule(predicate=predicate, order=order, rank=rank))
        seen_predicates.add(predicate_key)
    return tuple(rules)


def parse_format_rules(data: Mapping[str, object]) -> tuple[FormatRule, ...]:
    """Parse a ``[format]`` table into ordered rules."""
    rules: list[FormatRule] = []
    seen_predicates: set[tuple[str | None, str | None, tuple[str, ...]]] = set()
    for order, (key, value) in enumerate(data.items()):
        if not isinstance(value, str):
            raise RuleError(f"format.{key} must be a format string.")
        predicate = parse_predicate(str(key))
        predicate_key = _predicate_key(predicate)
        if predicate_key in seen_predicates:
            raise RuleError(f"Duplicate format predicate {key!r}.")
        seen_predicates.add(predicate_key)
        rules.append(
            FormatRule(
                format=parse_format(value),
                predicate=predicate,
                order=order,
            )
        )
    return tuple(rules)


def parse_collapse_rules(data: Mapping[str, object]) -> CollapseRules:
    """Parse ``[logseq.collapse]`` into a default and ordered overrides."""
    default = False
    rules: list[CollapseRule] = []
    seen_predicates: set[tuple[str | None, str | None, tuple[str, ...]]] = set()
    for order, (key, value) in enumerate(data.items()):
        key_text = str(key).strip()
        if key_text == "default":
            if not isinstance(value, bool):
                raise RuleError("logseq.collapse.default must be a boolean.")
            default = value
            continue
        if not isinstance(value, bool):
            raise RuleError(f"logseq.collapse.{key} must be a boolean.")
        predicate = parse_predicate(key_text)
        predicate_key = _predicate_key(predicate)
        if predicate_key in seen_predicates:
            raise RuleError(f"Duplicate collapse predicate {key!r}.")
        seen_predicates.add(predicate_key)
        rules.append(
            CollapseRule(
                collapsed=value,
                predicate=predicate,
                order=order,
            )
        )
    return CollapseRules(default=default, rules=tuple(rules))


def _choice(value: object, choices: frozenset[str], field: str) -> str:
    if not isinstance(value, str):
        raise RuleError(f"{field} must be one of {sorted(choices)}.")
    normalized = value.strip().lower()
    if normalized not in choices:
        raise RuleError(f"{field} must be one of {sorted(choices)}.")
    return normalized


def _validate_template(value: str, allowed: set[str], field: str) -> None:
    for match in _PLACEHOLDER_RE.finditer(value):
        name = match.group(1)
        if name not in allowed:
            raise RuleError(f"Unknown placeholder {{{name}}} in {field}.")
    remainder = _PLACEHOLDER_RE.sub("", value)
    if "{" in remainder or "}" in remainder:
        raise RuleError(f"Unbalanced braces in {field}.")


def _tag_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise RuleError(f"{field} must be an array of tag names.")
    tags: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise RuleError(f"{field} must contain only strings.")
        tag = normalize_tag(raw)
        if not tag:
            raise RuleError(f"{field} contains an empty tag.")
        if tag in tags:
            raise RuleError(f"Duplicate tag {tag!r} in {field}.")
        tags.append(tag)
    return tuple(tags)


def parse_source_config(data: Mapping[str, object]) -> SourceConfig:
    """Parse a ``[source]`` table."""
    unknown = [str(key) for key in data if str(key) not in _SOURCE_KEYS]
    if unknown:
        raise RuleError(f"Unknown source key {unknown[0]!r}.")

    scope = _choice(data.get("scope", "none"), SOURCE_SCOPES, "source.scope")
    when = _choice(
        data.get("when", "page_change"),
        SOURCE_WHEN,
        "source.when",
    )
    placement = _choice(
        data.get("placement", "next_line"),
        SOURCE_PLACEMENTS,
        "source.placement",
    )

    min_page_gap = data.get("min_page_gap", 0)
    if type(min_page_gap) is not int or min_page_gap < 0:
        raise RuleError("source.min_page_gap must be a non-negative integer.")

    link = data.get("link", True)
    if not isinstance(link, bool):
        raise RuleError("source.link must be a boolean.")

    template = data.get("template", "— {label}")
    if not isinstance(template, str):
        raise RuleError("source.template must be a string.")
    if "\n" in template or "\r" in template:
        raise RuleError("source.template must not contain newlines.")
    _validate_template(template, {"label"}, "source.template")

    page_label = data.get("page_label", "{page}")
    if not isinstance(page_label, str):
        raise RuleError("source.page_label must be a string.")
    if "\n" in page_label or "\r" in page_label:
        raise RuleError("source.page_label must not contain newlines.")
    _validate_template(page_label, {"page"}, "source.page_label")

    return SourceConfig(
        scope=scope,
        when=when,
        min_page_gap=min_page_gap,
        link=link,
        placement=placement,
        template=template,
        page_label=page_label,
    )


def parse_tag_config(data: Mapping[str, object]) -> TagConfig:
    """Parse a ``[tags]`` table."""
    unknown = [str(key) for key in data if str(key) not in _TAG_KEYS]
    if unknown:
        raise RuleError(f"Unknown tags key {unknown[0]!r}.")

    default = data.get("default", False)
    if not isinstance(default, bool):
        raise RuleError("tags.default must be a boolean.")

    hide = _tag_list(data.get("hide", ()), "tags.hide")
    show = _tag_list(data.get("show", ()), "tags.show")

    if default and show:
        raise RuleError("tags.show requires tags.default = false.")
    if not default and hide:
        raise RuleError("tags.hide requires tags.default = true.")

    return TagConfig(default=default, hide=hide, show=show)


def parse_background_config(data: Mapping[str, object]) -> BackgroundConfig:
    """Parse a ``[logseq.background]`` table."""
    unknown = [str(key) for key in data if str(key) not in _BACKGROUND_KEYS]
    if unknown:
        raise RuleError(f"Unknown logseq.background key {unknown[0]!r}.")

    mode = _choice(
        data.get("mode", "off"),
        BACKGROUND_MODES,
        "logseq.background.mode",
    )

    raw_palette = data.get("palette", ())
    if not isinstance(raw_palette, (list, tuple)):
        raise RuleError("logseq.background.palette must be an array.")
    palette: list[str] = []
    for raw in raw_palette:
        if not isinstance(raw, str):
            raise RuleError("logseq.background.palette must contain only strings.")
        color = raw.strip().lower()
        if not color:
            raise RuleError("logseq.background.palette contains an empty color.")
        if color not in LOGSEQ_BACKGROUND_COLORS:
            raise RuleError(
                f"Unknown background color {raw!r}; expected one of "
                f"{sorted(LOGSEQ_BACKGROUND_COLORS)}."
            )
        palette.append(color)

    if mode == "level" and not palette:
        raise RuleError(
            'logseq.background.palette is required when mode = "level".'
        )

    return BackgroundConfig(mode=mode, palette=tuple(palette))


def resolve_tree_rule(
    annotation: Annotation,
    rules: tuple[TreeRule, ...],
) -> TreeRule | None:
    """Return the most specific matching tree rule, if any."""
    best: TreeRule | None = None
    best_specificity: tuple[int, int, int, int] | None = None
    for rule in rules:
        if not rule.predicate.matches(annotation):
            continue
        specificity = rule.predicate.rank(annotation, rule.order)
        if best is None or best_specificity is None or specificity > best_specificity:
            best = rule
            best_specificity = specificity
    return best


def resolve_format(
    annotation: Annotation,
    rules: tuple[FormatRule, ...],
) -> Format:
    """Return the most specific matching format, or ``normal``."""
    best: FormatRule | None = None
    best_rank: tuple[int, int, int, int] | None = None
    for rule in rules:
        if not rule.predicate.matches(annotation):
            continue
        rank = rule.predicate.rank(annotation, rule.order)
        if best is None or best_rank is None or rank > best_rank:
            best = rule
            best_rank = rank
    return best.format if best is not None else NORMAL_FORMAT


def resolve_collapsed(
    annotation: Annotation,
    rules: CollapseRules,
) -> bool:
    """Return the most specific matching collapse state, or the default."""
    best: CollapseRule | None = None
    best_specificity: tuple[int, int, int, int] | None = None
    for rule in rules.rules:
        if not rule.predicate.matches(annotation):
            continue
        specificity = rule.predicate.rank(annotation, rule.order)
        if best is None or best_specificity is None or specificity > best_specificity:
            best = rule
            best_specificity = specificity
    return best.collapsed if best is not None else rules.default
