"""Better BibTeX JSON-RPC client for Zotero."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeAlias

from .models import Annotation, Attachment, Creator, Item, ItemRef, Tag

DEFAULT_BBT_PORT = 23119
DEFAULT_TIMEOUT = 10.0
BBT_TRANSLATOR = "36a3b0b5-bad0-4a04-b79b-441c7cef77db"

COLOR_CATEGORIES: Mapping[str, str] = {
    "#ffd400": "Yellow",
    "#ff6666": "Red",
    "#5fb236": "Green",
    "#2ea8e5": "Blue",
    "#a28ae5": "Purple",
    "#e56eee": "Magenta",
    "#f19837": "Orange",
    "#aaaaaa": "Gray",
}

Transport: TypeAlias = Callable[[urllib.request.Request, float], bytes]


class ZoteroError(Exception):
    """Base error for Zotero/BBT access."""


class ZoteroConnectionError(ZoteroError):
    """Zotero or Better BibTeX cannot be reached."""


class ZoteroRPCError(ZoteroError):
    """Better BibTeX returned a JSON-RPC error."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class ZoteroNoSelectionError(ZoteroError):
    """The user canceled or selected nothing in Zotero."""


class ZoteroDataError(ZoteroError):
    """Zotero returned data that cannot be used."""


class ZoteroNoAnnotationsError(ZoteroDataError):
    """The selected item has no annotations."""


def color_category(hex_color: str | None) -> str | None:
    """Map a Zotero annotation color to its category name."""
    if not hex_color:
        return None
    return COLOR_CATEGORIES.get(hex_color.strip().lower())


def attachment_key_from_path(path: str | None) -> str | None:
    """Extract the Zotero attachment key from a storage path."""
    if not path:
        return None
    match = re.search(r"(?:^|[\\/])storage[\\/]+([^\\/]+)[\\/]", path)
    if match:
        return match.group(1)
    parent = Path(path).parent.name
    return parent or None


def attachment_key_from_uri(uri: str | None) -> str | None:
    """Extract the Zotero attachment key from a Zotero URI."""
    if not uri:
        return None
    parsed = urllib.parse.urlparse(uri)
    path = parsed.path.rstrip("/")
    if not path:
        return None
    key = path.rsplit("/", 1)[-1]
    return key or None


def build_zotero_link(
    attachment_key: str,
    page_label: str = "",
    annotation_key: str = "",
) -> str:
    """Build a Zotero open-pdf link for an annotation."""
    base = f"zotero://open-pdf/library/items/{attachment_key}"
    query: list[tuple[str, str]] = []
    if page_label:
        query.append(("page", page_label))
    if annotation_key:
        query.append(("annotation", annotation_key))
    if not query:
        return base
    return f"{base}?{urllib.parse.urlencode(query)}"


def _default_transport(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class BBTClient:
    """Small synchronous client for Better BibTeX's local JSON-RPC API."""

    def __init__(
        self,
        port: int = DEFAULT_BBT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Transport | None = None,
    ) -> None:
        self.port = int(port)
        self.timeout = float(timeout)
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._transport = transport or _default_transport

    def probe(self) -> bool:
        """Return True when Zotero/BBT answers the cayw readiness probe."""
        raw = self._get("/better-bibtex/cayw", {"probe": "true"})
        try:
            return raw.decode("utf-8").strip().lower() == "ready"
        except UnicodeDecodeError as exc:
            raise ZoteroDataError("Zotero/BBT returned a non-UTF-8 probe response.") from exc

    def select_item(self) -> ItemRef:
        """Ask Zotero for an item selection through cayw."""
        raw = self._get(
            "/better-bibtex/cayw",
            {
                "format": "translate",
                "translator": BBT_TRANSLATOR,
                "exportNotes": "false",
            },
        )
        payload = self._decode_json(raw, "cayw response")
        items = payload.get("items") if isinstance(payload, dict) else None
        if not items:
            raise ZoteroNoSelectionError("No Zotero item was selected.")

        first = items[0]
        if not isinstance(first, dict):
            raise ZoteroDataError("Zotero returned an invalid cayw selection.")

        citation_key = first.get("citationKey") or first.get("citekey")
        if not citation_key:
            raise ZoteroDataError("Zotero selection did not include a citation key.")

        library_value = first.get("libraryID", first.get("library", 1))
        try:
            library_id = int(library_value)
        except (TypeError, ValueError):
            library_id = 1

        return ItemRef(citation_key=str(citation_key), library_id=library_id)

    def fetch_item(self, citekey: str, library_id: int = 1) -> Item:
        """Fetch item metadata and annotations for a citation key."""
        if not citekey:
            raise ZoteroDataError("A citation key is required.")

        export_result = self._rpc(
            "item.export",
            [[citekey], BBT_TRANSLATOR, int(library_id)],
        )
        export_data = self._parse_export_result(export_result)
        raw_items = export_data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ZoteroDataError(f"No item returned for citekey {citekey!r}.")

        raw_item = raw_items[0]
        if not isinstance(raw_item, dict):
            raise ZoteroDataError("Zotero returned an invalid item export.")

        citation_key = str(raw_item.get("citationKey") or citekey)
        title = str(raw_item.get("title") or "").strip() or citation_key
        item_key = str(raw_item.get("itemKey") or raw_item.get("key") or "")
        library_value = raw_item.get("libraryID", library_id)
        try:
            item_library_id = int(library_value)
        except (TypeError, ValueError):
            item_library_id = int(library_id)

        attachments_result = self._rpc(
            "item.attachments",
            [citation_key, item_library_id],
        )
        if not isinstance(attachments_result, list):
            raise ZoteroDataError("Zotero returned an invalid attachments response.")

        attachments = tuple(
            self._parse_attachment(raw)
            for raw in attachments_result
            if isinstance(raw, dict)
        )
        creators = tuple(
            self._parse_creator(raw)
            for raw in (raw_item.get("creators") or [])
            if isinstance(raw, dict)
        )
        item = Item(
            title=title,
            citation_key=citation_key,
            item_key=item_key,
            library_id=item_library_id,
            attachments=attachments,
            creators=creators,
        )
        if item.attachment is None:
            raise ZoteroNoAnnotationsError(
                f"No annotations found for citekey {citation_key!r}."
            )
        return item

    def _get(self, path: str, params: Mapping[str, str] | None = None) -> bytes:
        url = self.base_url + path
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Accept": "application/json"},
        )
        return self._send(request)

    def _rpc(self, method: str, params: list[Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        request = urllib.request.Request(
            self.base_url + "/better-bibtex/json-rpc",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        raw = self._send(request)
        response = self._decode_json(raw, f"{method} response")
        if not isinstance(response, dict):
            raise ZoteroDataError(f"Invalid JSON-RPC response for {method}.")

        error = response.get("error")
        if error:
            if isinstance(error, dict):
                message = str(error.get("message") or "Unknown Zotero/BBT error")
                code_value = error.get("code")
                code = code_value if isinstance(code_value, int) else None
            else:
                message = str(error)
                code = None
            raise ZoteroRPCError(message, code)

        if "result" not in response:
            raise ZoteroDataError(f"Zotero/BBT response for {method} has no result.")
        return response["result"]

    def _send(self, request: urllib.request.Request) -> bytes:
        try:
            return self._transport(request, self.timeout)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", "replace").strip()
            except Exception:
                body = ""
            detail = body or str(exc.reason)
            raise ZoteroRPCError(
                f"Zotero/BBT HTTP {exc.code}: {detail}",
                code=exc.code,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ZoteroConnectionError(
                f"Cannot connect to Zotero/BBT at {self.base_url}. "
                "Make sure Zotero is running and Better BibTeX is installed. "
                f"({reason})"
            ) from exc

    @staticmethod
    def _decode_json(raw: bytes, context: str) -> Any:
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZoteroDataError(f"Malformed JSON from {context}: {exc}") from exc

    @staticmethod
    def _parse_export_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            if len(result) > 2 and isinstance(result[2], str):
                result = result[2]
            else:
                raise ZoteroDataError("Unexpected item.export result array.")
        if not isinstance(result, str):
            raise ZoteroDataError("Unexpected item.export result type.")
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError as exc:
            raise ZoteroDataError(f"Malformed item.export JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ZoteroDataError("item.export did not return an object.")
        return parsed

    @staticmethod
    def _parse_creator(raw: dict[str, Any]) -> Creator:
        return Creator(
            first_name=str(raw.get("firstName") or ""),
            last_name=str(raw.get("lastName") or ""),
            name=str(raw.get("name") or ""),
            creator_type=str(raw.get("creatorType") or ""),
        )

    def _parse_attachment(self, raw: dict[str, Any]) -> Attachment:
        path = str(raw.get("path") or "")
        uri = str(raw.get("open") or "")
        key = attachment_key_from_uri(uri) or attachment_key_from_path(path)
        if not key:
            raise ZoteroDataError("Attachment has no resolvable Zotero key.")

        raw_annotations = raw.get("annotations") or []
        if not isinstance(raw_annotations, list):
            raise ZoteroDataError("Attachment annotations are not a list.")

        annotations = tuple(
            sorted(
                (
                    self._parse_annotation(annotation, key)
                    for annotation in raw_annotations
                    if isinstance(annotation, dict)
                ),
                key=lambda annotation: annotation.sort_index,
            )
        )
        return Attachment(key=key, path=path, uri=uri, annotations=annotations)

    @staticmethod
    def _parse_annotation(raw: dict[str, Any], attachment_key: str) -> Annotation:
        key = str(raw.get("key") or "")
        if not key:
            raise ZoteroDataError("Annotation has no key.")

        color_hex = str(raw.get("annotationColor") or "")
        page_label = str(raw.get("annotationPageLabel") or "")
        tags_raw = raw.get("tags") or []
        tags = tuple(
            Tag(str(tag.get("tag")))
            for tag in tags_raw
            if isinstance(tag, dict) and tag.get("tag")
        )

        return Annotation(
            key=key,
            annotation_type=str(raw.get("annotationType") or ""),
            color_hex=color_hex,
            color_category=color_category(color_hex),
            page_label=page_label,
            sort_index=str(raw.get("annotationSortIndex") or ""),
            text=str(raw.get("annotationText") or ""),
            comment=str(raw.get("annotationComment") or ""),
            tags=tags,
            desktop_uri=build_zotero_link(attachment_key, page_label, key),
        )
