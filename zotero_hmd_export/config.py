"""Project configuration loading and full-config generation."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

from .rules import (
    BackgroundConfig,
    CollapseRules,
    FormatRule,
    RuleError,
    SourceConfig,
    TagConfig,
    TreeRule,
    parse_background_config,
    parse_collapse_rules,
    parse_format_rules,
    parse_source_config,
    parse_tag_config,
    parse_tree_rules,
)

PROJECT_CONFIG_NAME = "zotero-hmd-export.toml"
DEFAULT_BOOKS_NAME = "books.toml"
DEFAULT_FILE_NAME = "{title}.md"
DEFAULT_ON_EXISTING = "overwrite"
DEFAULT_BBT_PORT = 23119
ON_EXISTING_VALUES = {"overwrite", "error"}

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_PATH = _PACKAGE_DIR / "templates" / "config.toml"


class ConfigError(Exception):
    """Configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    output_dir: Path
    books_path: Path
    file_name: str
    include_properties: bool
    on_existing: str
    bbt_port: int
    tree_rules: tuple[TreeRule, ...]
    format_rules: tuple[FormatRule, ...]
    collapse_rules: CollapseRules
    source: SourceConfig | None
    tags: TagConfig | None
    background: BackgroundConfig | None
    project_path: Path


def find_project_config(start: Path | None = None) -> Path:
    """Find zotero-hmd-export.toml in the current directory."""
    base = (start or Path.cwd()).resolve()
    path = base / PROJECT_CONFIG_NAME
    if not path.is_file():
        raise ConfigError(
            f"Project config not found: {path}. Run 'zotero-hmd-export init' first."
        )
    return path


def load_config(project_path: Path | str | None = None) -> Config:
    """Load the project config, with built-in defaults for missing sections."""
    project_file = (
        Path(project_path).expanduser()
        if project_path is not None
        else find_project_config()
    )
    project_file = project_file.resolve()
    if not project_file.is_file():
        raise ConfigError(f"Project config not found: {project_file}")

    project_data = _read_toml(project_file, "project config")
    project = project_data.get("project")
    if not isinstance(project, dict):
        raise ConfigError(f"{project_file}: missing [project] section.")

    output_value = project.get("output_dir")
    if not isinstance(output_value, str) or not output_value.strip():
        raise ConfigError(f"{project_file}: [project].output_dir is required.")
    output_dir = _resolve_path(output_value, project_file.parent, "output_dir")

    books_value = project.get("books", DEFAULT_BOOKS_NAME)
    if not isinstance(books_value, str) or not books_value.strip():
        raise ConfigError(f"{project_file}: [project].books must be a path.")
    books_path = _resolve_path(books_value, project_file.parent, "books")

    file_name = project.get("file_name", DEFAULT_FILE_NAME)
    include_properties = project.get("include_properties", False)
    on_existing = project.get("on_existing", DEFAULT_ON_EXISTING)

    zotero = _table(project_data.get("zotero"), "zotero")
    bbt_port = zotero.get("bbt_port", DEFAULT_BBT_PORT)

    try:
        tree_rules = parse_tree_rules(_table(project_data.get("tree"), "tree"))
        format_rules = parse_format_rules(
            _table(project_data.get("format"), "format")
        )
        logseq = _table(project_data.get("logseq"), "logseq")
        collapse_rules = parse_collapse_rules(
            _table(logseq.get("collapse"), "logseq.collapse")
        )
        background_data = logseq.get("background")
        background = (
            None
            if background_data is None
            else parse_background_config(
                _table(background_data, "logseq.background")
            )
        )
        source_data = project_data.get("source")
        source = (
            None
            if source_data is None
            else parse_source_config(_table(source_data, "source"))
        )
        tags_data = project_data.get("tags")
        tags = (
            None
            if tags_data is None
            else parse_tag_config(_table(tags_data, "tags"))
        )
    except RuleError as exc:
        raise ConfigError(f"{project_file}: {exc}") from exc

    _validate(
        file_name=file_name,
        include_properties=include_properties,
        on_existing=on_existing,
        bbt_port=bbt_port,
        project_file=project_file,
    )

    return Config(
        output_dir=output_dir,
        books_path=books_path,
        file_name=str(file_name),
        include_properties=bool(include_properties),
        on_existing=str(on_existing),
        bbt_port=int(bbt_port),
        tree_rules=tree_rules,
        format_rules=format_rules,
        collapse_rules=collapse_rules,
        source=source,
        tags=tags,
        background=background,
        project_path=project_file,
    )


def write_project_config(
    path: Path | str,
    *,
    output_dir: Path | str,
    books: str,
    file_name: str,
    include_properties: bool = False,
    on_existing: str = DEFAULT_ON_EXISTING,
) -> Path:
    """Write a complete, self-documenting project config."""
    config_path = Path(path).expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config template {_TEMPLATE_PATH}: {exc}") from exc

    values = {
        "OUTPUT_DIR": _toml_quote(str(output_dir)),
        "BOOKS": _toml_quote(books),
        "FILE_NAME": _toml_quote(file_name),
        "INCLUDE_PROPERTIES_VALUE": "true" if include_properties else "false",
        "ON_EXISTING_VALUE": _toml_quote(on_existing),
    }
    try:
        content = Template(template).substitute(values)
    except (KeyError, ValueError) as exc:
        raise ConfigError(
            f"Config template {_TEMPLATE_PATH} has an invalid placeholder: {exc}"
        ) from exc
    config_path.write_text(content, encoding="utf-8")
    return config_path


def _validate(
    *,
    file_name: Any,
    include_properties: Any,
    on_existing: Any,
    bbt_port: Any,
    project_file: Path,
) -> None:
    if not isinstance(file_name, str) or not file_name.strip():
        raise ConfigError(f"{project_file}: file_name must be a non-empty string.")
    if not isinstance(include_properties, bool):
        raise ConfigError(f"{project_file}: include_properties must be a boolean.")
    if not isinstance(on_existing, str) or on_existing not in ON_EXISTING_VALUES:
        raise ConfigError(
            f"{project_file}: on_existing must be one of {sorted(ON_EXISTING_VALUES)}."
        )
    if not isinstance(bbt_port, int) or not 1 <= bbt_port <= 65535:
        raise ConfigError(f"{project_file}: zotero.bbt_port must be 1..65535.")


def _read_toml(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"Cannot read {label} {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{label} {path} did not contain a table.")
    return data


def _table(value: Any, label: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigError(f"[{label}] must be a table.")
    return value


def _resolve_path(value: str, base: Path, field: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
