"""Catalog completeness and native locale fallback checks."""
from string import Formatter
from unittest.mock import patch
import unittest

from swirphoneos.i18n import CATALOGS, detect_language, language_code, translate


def _format_values(template: str) -> dict[str, object]:
    """Build deterministic dummy values for exactly the placeholders in a source string."""
    values: dict[str, object] = {}
    for _, field_name, format_spec, _ in Formatter().parse(template):
        if not field_name:
            continue
        name = field_name.split(".", 1)[0].split("[", 1)[0]
        # Existing elapsed-time UI expects a number; textual readiness fields do
        # not use numeric format specs. Keep numeric specs future-safe too.
        if name == "seconds" or format_spec.endswith(("d", "f", "g")):
            values[name] = 1
        else:
            values[name] = "test"
    return values


class LanguageTests(unittest.TestCase):
    def test_catalogs_complete(self):
        source = CATALOGS["en"]
        for language, catalog in CATALOGS.items():
            with self.subTest(language=language):
                self.assertEqual(set(catalog), set(source))
                for key in catalog:
                    self.assertTrue(translate(language, key, **_format_values(source[key])))

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
