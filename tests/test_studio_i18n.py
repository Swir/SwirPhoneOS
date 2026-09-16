"""Catalog completeness and native locale fallback checks."""
from unittest.mock import patch
import unittest
from swirphoneos.i18n import CATALOGS, detect_language, language_code, translate


class LanguageTests(unittest.TestCase):
    def test_catalogs_complete(self):
        for language, catalog in CATALOGS.items():
            with self.subTest(language=language):
                self.assertEqual(set(catalog), set(CATALOGS["en"]))
                for key in catalog:
                    self.assertTrue(translate(language, key, seconds=1))

    def test_polish_locale(self):
        self.assertEqual(language_code("pl_PL.UTF-8"), "pl")

    def test_bcp47_locale(self):
        self.assertEqual(language_code("PL-pl"), "pl")

    def test_norwegian(self):
        self.assertEqual(language_code("nb_NO"), "nb")
        self.assertEqual(language_code("no-NO"), "nb")

    def test_unsupported_defaults_to_english(self):
        self.assertEqual(language_code("ja_JP"), "en")
        self.assertEqual(language_code(None), "en")
        self.assertEqual(language_code("C.UTF-8"), "en")

    def test_unknown_catalog_uses_english(self):
        self.assertEqual(translate("xx", "scan"), CATALOGS["en"]["scan"])

    def test_missing_translation_falls_back(self):
        with patch.dict(CATALOGS, {"sample": {}}):
            self.assertEqual(translate("sample", "scan"), CATALOGS["en"]["scan"])

    def test_lc_all_precedes_lang(self):
        with patch("sys.platform", "linux"), patch.dict("os.environ", {"LC_ALL": "pl_PL", "LANG": "nb_NO"}, clear=True):
            self.assertEqual(detect_language(), "pl")

    def test_lc_messages_precedes_lang(self):
        with patch("sys.platform", "linux"), patch.dict("os.environ", {"LC_MESSAGES": "nb_NO", "LANG": "pl_PL"}, clear=True):
            self.assertEqual(detect_language(), "nb")

    def test_empty_environment_falls_back_to_native_locale(self):
        with patch("sys.platform", "linux"), patch.dict("os.environ", {}, clear=True), patch("locale.getlocale", return_value=("pl_PL", None)):
            self.assertEqual(detect_language(), "pl")

    def test_invalid_locale_is_safe(self):
        with patch("sys.platform", "linux"), patch.dict("os.environ", {}, clear=True), patch("locale.getlocale", side_effect=ValueError):
            self.assertEqual(detect_language(), "en")

    def test_format_in_every_language(self):
        for language in CATALOGS:
            self.assertIn("17s", translate(language, "running", seconds=17))
