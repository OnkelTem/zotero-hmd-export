"""Dataclasses for Zotero items, attachments, and annotations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tag:
    """A Zotero annotation tag."""

    name: str


@dataclass(frozen=True, slots=True)
class Creator:
    """A Zotero creator (author, editor, etc.)."""

    first_name: str
    last_name: str
    name: str
    creator_type: str


@dataclass(frozen=True, slots=True)
class Annotation:
    """A single Zotero PDF annotation."""

    key: str
    annotation_type: str
    color_hex: str
    color_category: str | None
    page_label: str
    sort_index: str
    text: str
    comment: str
    tags: tuple[Tag, ...]
    desktop_uri: str


@dataclass(frozen=True, slots=True)
class Attachment:
    """A PDF attachment with its annotations."""

    key: str
    path: str
    uri: str
    annotations: tuple[Annotation, ...]

    @property
    def has_annotations(self) -> bool:
        return bool(self.annotations)


@dataclass(frozen=True, slots=True)
class Item:
    """A Zotero item and the attachments relevant to the export."""

    title: str
    citation_key: str
    item_key: str
    library_id: int
    attachments: tuple[Attachment, ...]
    creators: tuple[Creator, ...] = ()

    @property
    def attachment(self) -> Attachment | None:
        """Return the first attachment that contains annotations."""
        return next((a for a in self.attachments if a.annotations), None)

    @property
    def author(self) -> str:
        """Return the first creator's last name (or single-field name)."""
        for creator in self.creators:
            value = creator.last_name or creator.name
            if value:
                return value
        return ""


@dataclass(frozen=True, slots=True)
class ItemRef:
    """An item selected through Better BibTeX ``cayw``."""

    citation_key: str
    library_id: int
