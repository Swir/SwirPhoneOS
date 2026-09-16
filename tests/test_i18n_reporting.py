from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.i18n import normalize_language, system_language, tr
from swirphoneos.reporting import ReportError, build_export, write_export


class LanguageTests(unittest.TestCase):
    def test_polish_locale(self) -> None:
        self.assertEqual(normalize_language("pl_PL"), "pl")

    def test_norwegian_variants(self) -> None:
        self.assertEqual(normalize_language("nb_NO"), "no")
        self.assertEqual(normalize_language("nn-NO"), "no")

    def test_unsupported_locale_falls_back_to_english(self) -> None:
        self.assertEqual(normalize_language("fr_FR"), "en")
        self.assertEqual(normalize_language(None), "en")

    def test_injected_system_language_is_deterministic(self) -> None:
        self.assertEqual(system_language("pl-PL"), "pl")

    def test_translations_have_expected_fallback(self) -> None:
        self.assertEqual(tr("app_title", "pl"), "SwirPhoneStudio")
        self.assertIn("READ-ONLY", tr("preview", "unsupported"))

    def test_unknown_key_raises(self) -> None:
        with self.assertRaises(KeyError):
            tr("does_not_exist", "en")


class ReportTests(unittest.TestCase):
    def test_build_sanitized_adb_report(self) -> None:
        payload = build_export("adb", {"model": "Example", "flash_allowed": False})
        self.assertEqual(payload["application"], "SwirPhoneStudio")
        self.assertEqual(payload["report_kind"], "adb")
        self.assertEqual(payload["report"]["model"], "Example")

    def test_rejects_unknown_report_kind(self) -> None:
        with self.assertRaises(ReportError):
            build_export("raw-shell", {})

    def test_rejects_serial_field_anywhere(self) -> None:
        with self.assertRaises(ReportError):
            build_export("adb", {"nested": {"device_serial": "PRIVATE"}})

    def test_rejects_imei_field_anywhere(self) -> None:
        with self.assertRaises(ReportError):
            build_export("adb", {"identity": {"imei": "PRIVATE"}})

    def test_rejects_oversized_text(self) -> None:
        with self.assertRaises(ReportError):
            build_export("profiles", {"notes": "x" * 9000})

    def test_write_export_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            write_export(path, "fastboot", {"product_reported": "avicii", "flash_allowed": False})
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["report_kind"], "fastboot")
            self.assertFalse(payload["report"]["flash_allowed"])

    def test_write_requires_json_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.txt"
            with self.assertRaises(ReportError):
                write_export(path, "profiles", {})


if __name__ == "__main__":
    unittest.main()
