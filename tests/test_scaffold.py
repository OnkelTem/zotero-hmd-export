import unittest

from zotero_hmd_export import __version__
from zotero_hmd_export.cli import build_parser


class ScaffoldTest(unittest.TestCase):
    def test_version(self) -> None:
        self.assertEqual(__version__, "0.1.0")

    def test_parser_accepts_export(self) -> None:
        args = build_parser().parse_args(["export", "--book", "Example2024"])
        self.assertEqual(args.command, "export")
        self.assertEqual(args.book, "Example2024")

    def test_parser_accepts_doctor(self) -> None:
        args = build_parser().parse_args(["doctor"])
        self.assertEqual(args.command, "doctor")


if __name__ == "__main__":
    unittest.main()
