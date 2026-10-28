"""Tests for the Better BibTeX client and data models."""

from __future__ import annotations

import json
import unittest
import urllib.error
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from pathlib import Path

from zotero_hmd_export.models import Annotation, Attachment, Creator, Item, ItemRef, Tag
from zotero_hmd_export.zotero import (
    BBT_TRANSLATOR,
    BBTClient,
    ZoteroConnectionError,
    ZoteroDataError,
    ZoteroNoSelectionError,
    ZoteroRPCError,
    attachment_key_from_path,
    attachment_key_from_uri,
    build_zotero_link,
    color_category,
)

FIXTURES = Path(__file__).parent / "fixtures"
CITEKEY = "Kahneman2011Thinking"


def load_json(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def rpc_response(result: object) -> bytes:
    return json.dumps(
        {"jsonrpc": "2.0", "result": result, "id": None},
        ensure_ascii=False,
    ).encode("utf-8")


class FakeTransport:
    def __init__(self, handler: Callable[[object, float], bytes]) -> None:
        self.handler = handler
        self.requests: list[object] = []

    def __call__(self, request: object, timeout: float) -> bytes:
        self.requests.append(request)
        return self.handler(request, timeout)


class ZoteroClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.export_item = load_json("item_export_item.json")
        self.attachments_result = load_json("item_attachments_result.json")
        self.cayw_items = load_json("cayw_items.json")
        self.error_response = load_json("error_not_found.json")
        self.probe_bytes = (FIXTURES / "probe.txt").read_bytes()

    def make_client(
        self,
        handler: Callable[[object, float], bytes],
    ) -> tuple[BBTClient, FakeTransport]:
        transport = FakeTransport(handler)
        return BBTClient(transport=transport), transport

    def default_handler(self, request: object, timeout: float) -> bytes:
        url = request.full_url  # type: ignore[attr-defined]
        if "probe=true" in url:
            return self.probe_bytes
        if "/better-bibtex/cayw" in url:
            return json.dumps(self.cayw_items, ensure_ascii=False).encode("utf-8")

        body = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
        method = body["method"]
        if method == "item.export":
            result = json.dumps(
                {"items": [self.export_item]},
                ensure_ascii=False,
            )
            return rpc_response(result)
        if method == "item.attachments":
            return rpc_response(self.attachments_result)
        raise AssertionError(f"Unexpected method: {method}")

    def test_probe_ready(self) -> None:
        client, _ = self.make_client(self.default_handler)
        self.assertTrue(client.probe())

    def test_probe_not_ready(self) -> None:
        client, _ = self.make_client(lambda request, timeout: b"busy")
        self.assertFalse(client.probe())

    def test_select_item(self) -> None:
        client, _ = self.make_client(self.default_handler)
        ref = client.select_item()
        self.assertEqual(ref, ItemRef(citation_key=CITEKEY, library_id=1))

    def test_select_item_accepts_citation_key_field(self) -> None:
        def handler(request: object, timeout: float) -> bytes:
            return json.dumps(
                {"items": [{"citationKey": "OtherKey", "libraryID": 2}]}
            ).encode("utf-8")

        client, _ = self.make_client(handler)
        ref = client.select_item()
        self.assertEqual(ref, ItemRef(citation_key="OtherKey", library_id=2))

    def test_select_item_empty(self) -> None:
        def handler(request: object, timeout: float) -> bytes:
            return json.dumps({"items": []}).encode("utf-8")

        client, _ = self.make_client(handler)
        with self.assertRaises(ZoteroNoSelectionError):
            client.select_item()

    def test_fetch_item_parses_metadata_and_annotations(self) -> None:
        client, transport = self.make_client(self.default_handler)
        item = client.fetch_item(CITEKEY)

        self.assertEqual(item.title, "Thinking, Fast and Slow")
        self.assertEqual(item.citation_key, CITEKEY)
        self.assertEqual(item.item_key, "AAAA1111")
        self.assertEqual(item.library_id, 1)
        self.assertEqual(item.creators, ())
        self.assertEqual(item.author, "")

        attachment = item.attachment
        self.assertIsNotNone(attachment)
        assert attachment is not None
        self.assertEqual(attachment.key, "BBBB2222")
        self.assertEqual(len(attachment.annotations), 5)

        sort_indexes = [annotation.sort_index for annotation in attachment.annotations]
        self.assertEqual(sort_indexes, sorted(sort_indexes))

        first = attachment.annotations[0]
        self.assertEqual(first.key, "HEADING1")
        self.assertEqual(first.annotation_type, "highlight")
        self.assertEqual(first.color_hex, "#ffd400")
        self.assertEqual(first.color_category, "Yellow")
        self.assertEqual(first.page_label, "7")
        self.assertEqual(first.comment, "Section opener")
        self.assertEqual(
            first.desktop_uri,
            "zotero://open-pdf/library/items/BBBB2222"
            "?page=7&annotation=HEADING1",
        )

        tagged = next(annotation for annotation in attachment.annotations if annotation.tags)
        self.assertIn(Tag("example"), tagged.tags)
        self.assertEqual(len(transport.requests), 2)

    def test_fetch_item_accepts_array_export_result(self) -> None:
        def handler(request: object, timeout: float) -> bytes:
            body = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
            if body["method"] == "item.export":
                result = json.dumps(
                    {"items": [self.export_item]},
                    ensure_ascii=False,
                )
                return rpc_response([None, None, result])
            return rpc_response(self.attachments_result)

        client, _ = self.make_client(handler)
        item = client.fetch_item(CITEKEY)
        self.assertEqual(item.citation_key, CITEKEY)

    def test_fetch_item_parses_creators(self) -> None:
        export_item = dict(self.export_item)
        export_item["creators"] = [
            {
                "firstName": "Daniel",
                "lastName": "Kahneman",
                "name": "",
                "creatorType": "author",
            }
        ]

        def handler(request: object, timeout: float) -> bytes:
            body = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
            if body["method"] == "item.export":
                result = json.dumps(
                    {"items": [export_item]},
                    ensure_ascii=False,
                )
                return rpc_response(result)
            return rpc_response(self.attachments_result)

        client, _ = self.make_client(handler)
        item = client.fetch_item(CITEKEY)
        self.assertEqual(item.author, "Kahneman")
        self.assertEqual(item.creators[0].creator_type, "author")

    def test_fetch_item_without_annotations(self) -> None:
        empty_attachments = [
            {
                "path": "/home/user/Zotero/storage/BBBB2222/book.pdf",
                "open": "zotero://open-pdf/library/items/BBBB2222",
                "annotations": [],
            }
        ]

        def handler(request: object, timeout: float) -> bytes:
            body = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
            if body["method"] == "item.export":
                result = json.dumps(
                    {"items": [self.export_item]},
                    ensure_ascii=False,
                )
                return rpc_response(result)
            return rpc_response(empty_attachments)

        client, _ = self.make_client(handler)
        with self.assertRaises(ZoteroDataError):
            client.fetch_item(CITEKEY)

    def test_rpc_error(self) -> None:
        def handler(request: object, timeout: float) -> bytes:
            return json.dumps(self.error_response, ensure_ascii=False).encode("utf-8")

        client, _ = self.make_client(handler)
        with self.assertRaises(ZoteroRPCError) as raised:
            client.fetch_item("NoSuchKey123")
        self.assertEqual(raised.exception.code, -32602)
        self.assertIn("NoSuchKey123", str(raised.exception))

    def test_connection_error(self) -> None:
        def handler(request: object, timeout: float) -> bytes:
            raise urllib.error.URLError("connection refused")

        client, _ = self.make_client(handler)
        with self.assertRaises(ZoteroConnectionError) as raised:
            client.fetch_item(CITEKEY)
        self.assertIn("Cannot connect to Zotero/BBT", str(raised.exception))

    def test_malformed_json(self) -> None:
        client, _ = self.make_client(lambda request, timeout: b"not json")
        with self.assertRaises(ZoteroDataError):
            client.fetch_item(CITEKEY)


class HelperTest(unittest.TestCase):
    def test_color_category(self) -> None:
        self.assertEqual(color_category("#ffd400"), "Yellow")
        self.assertEqual(color_category("#FFD400"), "Yellow")
        self.assertIsNone(color_category("#123456"))
        self.assertIsNone(color_category(""))

    def test_attachment_key_from_path(self) -> None:
        self.assertEqual(
            attachment_key_from_path(
                "/home/user/Zotero/storage/BBBB2222/book.pdf"
            ),
            "BBBB2222",
        )
        self.assertIsNone(attachment_key_from_path(""))

    def test_attachment_key_from_uri(self) -> None:
        self.assertEqual(
            attachment_key_from_uri("zotero://open-pdf/library/items/BBBB2222"),
            "BBBB2222",
        )
        self.assertEqual(
            attachment_key_from_uri(
                "http://zotero.org/users/local/abc/items/BBBB2222"
            ),
            "BBBB2222",
        )
        self.assertIsNone(attachment_key_from_uri(""))

    def test_build_zotero_link(self) -> None:
        self.assertEqual(
            build_zotero_link("BBBB2222", "7", "YJ7ZGP84"),
            "zotero://open-pdf/library/items/BBBB2222"
            "?page=7&annotation=YJ7ZGP84",
        )


class ModelTest(unittest.TestCase):
    def test_annotation_is_frozen(self) -> None:
        annotation = Annotation(
            key="A",
            annotation_type="highlight",
            color_hex="#ffd400",
            color_category="Yellow",
            page_label="1",
            sort_index="1",
            text="text",
            comment="",
            tags=(),
            desktop_uri="",
        )
        with self.assertRaises(FrozenInstanceError):
            annotation.text = "changed"  # type: ignore[misc]

    def test_item_author_uses_first_creator(self) -> None:
        item = Item(
            title="Title",
            citation_key="Key",
            item_key="ITEM",
            library_id=1,
            attachments=(),
            creators=(
                Creator("", "Kahneman", "", "author"),
                Creator("", "Newport", "", "author"),
            ),
        )
        self.assertEqual(item.author, "Kahneman")

    def test_item_selects_first_attachment_with_annotations(self) -> None:
        empty = Attachment(key="EMPTY", path="", uri="", annotations=())
        annotation = Annotation(
            key="A",
            annotation_type="highlight",
            color_hex="#ffd400",
            color_category="Yellow",
            page_label="1",
            sort_index="1",
            text="text",
            comment="",
            tags=(),
            desktop_uri="",
        )
        filled = Attachment(
            key="FILLED",
            path="",
            uri="",
            annotations=(annotation,),
        )
        item = Item(
            title="Title",
            citation_key="Key",
            item_key="ITEM",
            library_id=1,
            attachments=(empty, filled),
        )
        self.assertIs(item.attachment, filled)


if __name__ == "__main__":
    unittest.main()
