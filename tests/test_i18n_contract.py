"""Global localization contract checks."""
from __future__ import annotations

import copy
from unittest.mock import patch
import unittest

from swirphoneos.i18n import (
    CATALOGS,
    LOCALES,
    LocalizationError,
    _merge_catalog_fragment,
    _validate_catalog_document,
    catalog_summary,
    detect_language,
    language_code,
    text_direction,
    translate,
)


class GlobalI18nTests(unittest.TestCase):
    def test_global_catalog_has_multiple_regions_and_rtl(self):
        self.assertGreaterEqual(len(CATALOGS), 8)
        self.assertIn("ar", CATALOGS)
        self.assertEqual(text_direction("ar-SA"), "rtl")
        self.assertEqual(text_direction("pl-PL"), "ltr")

    def test_common_regional_locales_resolve(self):
        cases = {
            "de-DE": "de",
            "es-MX": "es",
            "fr-CA": "fr",
            "pt-BR": "pt",
            "ar-SA": "ar",
            "no-NO": "nb",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(language_code(raw), expected)

    def test_catalog_summary_is_truthful(self):
        summary = catalog_summary()
        self.assertEqual(summary["source_locale"], "en")
        self.assertEqual(summary["locale_count"], len(CATALOGS))
        self.assertEqual(summary["string_count"], len(CATALOGS["en"]))
        for row in summary["locales"]:
            self.assertGreater(row["coverage_percent"], 0)
            self.assertLessEqual(row["coverage_percent"], 100.0)

    def test_studio_readiness_fragment_is_complete_in_every_locale(self):
        required = {
            "review_readiness", "readiness_failed", "readiness_loaded",
            "readiness_summary", "yes", "no", "none",
        }
        for code, catalog in CATALOGS.items():
            with self.subTest(locale=code):
                self.assertTrue(required.issubset(catalog))
        summary = catalog_summary()
        self.assertTrue(all(row["coverage_percent"] == 100.0 for row in summary["locales"]))

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(LocalizationError):
            translate("en", "definitely_missing")

    def test_placeholder_mismatch_is_rejected(self):
        document = {
            "schema_version": 1,
            "source_locale": "en",
            "locales": {
                "en": {"name": "English", "direction": "ltr", "strings": {"running": "Running {seconds}s"}},
                "pl": {"name": "Polski", "direction": "ltr", "strings": {"running": "Działa {minutes}m"}},
            },
        }
        with self.assertRaises(LocalizationError):
            _validate_catalog_document(document)

    def test_fragment_requires_every_registered_locale(self):
        document = {
            "schema_version": 1,
            "source_locale": "en",
            "locales": {
                "en": {"name": "English", "direction": "ltr", "strings": {"base": "Base"}},
                "pl": {"name": "Polski", "direction": "ltr", "strings": {"base": "Baza"}},
            },
        }
        fragment = {"schema_version": 1, "source_locale": "en", "strings": {"en": {"new": "New"}}}
        with self.assertRaises(LocalizationError):
            _merge_catalog_fragment(copy.deepcopy(document), fragment)

    def test_fragment_rejects_key_coverage_drift(self):
        document = {
            "schema_version": 1,
            "source_locale": "en",
            "locales": {
                "en": {"name": "English", "direction": "ltr", "strings": {"base": "Base"}},
                "pl": {"name": "Polski", "direction": "ltr", "strings": {"base": "Baza"}},
            },
        }
        fragment = {
            "schema_version": 1,
            "source_locale": "en",
            "strings": {"en": {"new": "New"}, "pl": {"other": "Inne"}},
        }
        with self.assertRaises(LocalizationError):
            _merge_catalog_fragment(copy.deepcopy(document), fragment)

    def test_fragment_cannot_override_base_string(self):
        document = {
            "schema_version": 1,
            "source_locale": "en",
            "locales": {
                "en": {"name": "English", "direction": "ltr", "strings": {"base": "Base"}},
                "pl": {"name": "Polski", "direction": "ltr", "strings": {"base": "Baza"}},
            },
        }
        fragment = {
            "schema_version": 1,
            "source_locale": "en",
            "strings": {"en": {"base": "Override"}, "pl": {"base": "Nadpisz"}},
        }
        with self.assertRaises(LocalizationError):
            _merge_catalog_fragment(copy.deepcopy(document), fragment)

    def test_partial_catalog_uses_english_fallback(self):
        with patch.dict(CATALOGS, {"sample": {"scan": "Localized"}}, clear=False):
            self.assertEqual(translate("sample", "scan"), "Localized")
            self.assertEqual(translate("sample", "close"), CATALOGS["en"]["close"])

    def test_environment_detects_rtl_language(self):
        with patch("sys.platform", "linux"), patch.dict("os.environ", {"LANG": "ar_SA.UTF-8"}, clear=True):
            self.assertEqual(detect_language(), "ar")

    def test_loaded_locale_metadata_matches_catalogs(self):
        self.assertEqual(set(LOCALES), set(CATALOGS))


if __name__ == "__main__":
    unittest.main()
