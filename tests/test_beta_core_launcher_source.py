import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform" / "aosp_product" / "apps" / "SwirLauncher"
STAGE = ROOT / "platform" / "aosp_product" / "stage_manifest.d" / "beta-core-launcher.json"
CF_PRODUCT = ROOT / "platform" / "aosp_product" / "swirphoneos_cf_x86_64.mk"
GSI_PRODUCT = ROOT / "platform" / "aosp_product" / "swirphoneos_gsi_arm64.mk"
ANDROID = "{http://schemas.android.com/apk/res/android}"
LOCALES = ("", "-pl", "-nb", "-de", "-es", "-fr", "-pt", "-ar")


class BetaCoreLauncherSourceTest(unittest.TestCase):
    def test_permission_free_home_contract(self) -> None:
        root = ET.parse(APP / "AndroidManifest.xml").getroot()
        self.assertEqual(root.attrib.get("package"), "org.swir.phoneos.launcher")
        self.assertEqual(root.findall("uses-permission"), [])

        application = root.find("application")
        self.assertIsNotNone(application)
        self.assertEqual(application.attrib.get(ANDROID + "supportsRtl"), "true")
        self.assertEqual(application.attrib.get(ANDROID + "localeConfig"), "@xml/locales_config")

        activity = application.find("activity")
        self.assertIsNotNone(activity)
        self.assertEqual(activity.attrib.get(ANDROID + "exported"), "true")
        filters = activity.findall("intent-filter")
        categories = {
            node.attrib.get(ANDROID + "name")
            for intent_filter in filters
            for node in intent_filter.findall("category")
        }
        actions = {
            node.attrib.get(ANDROID + "name")
            for intent_filter in filters
            for node in intent_filter.findall("action")
        }
        self.assertIn("android.intent.action.MAIN", actions)
        self.assertIn("android.intent.category.HOME", categories)
        self.assertIn("android.intent.category.DEFAULT", categories)

        query_categories = {
            node.attrib.get(ANDROID + "name")
            for intent in root.findall("./queries/intent")
            for node in intent.findall("category")
        }
        self.assertIn("android.intent.category.LAUNCHER", query_categories)

    def test_beta_products_replace_stock_home_with_swir_launcher(self) -> None:
        for product in (CF_PRODUCT, GSI_PRODUCT):
            text = product.read_text(encoding="utf-8")
            self.assertIn("SwirLauncher", text)
            self.assertIn("filter-out Launcher3 Launcher3QuickStep Launcher3QuickStepGo", text)

    def test_first_run_setup_is_local_and_delegates_authoritative_settings(self) -> None:
        source = (APP / "src/org/swir/phoneos/launcher/MainActivity.java").read_text(encoding="utf-8")
        policy = (APP / "src/org/swir/phoneos/launcher/LauncherPolicy.java").read_text(encoding="utf-8")
        self.assertIn("SharedPreferences", source)
        self.assertIn("Settings.ACTION_LOCALE_SETTINGS", source)
        self.assertIn("Settings.ACTION_PRIVACY_SETTINGS", source)
        self.assertIn("Settings.ACTION_SECURITY_SETTINGS", source)
        self.assertIn("LauncherPolicy.setupReady", source)
        self.assertIn("return languageReviewed && privacyReviewed && securityReviewed", policy)
        self.assertIn("PackageManager", source)
        self.assertIn("Intent.CATEGORY_LAUNCHER", source)
        self.assertNotRegex(source, r"setText\(\s*\"")
        for forbidden in (
            "Runtime.getRuntime",
            "ProcessBuilder",
            "HttpURLConnection",
            "java.net.Socket",
            "Settings.Secure.put",
            "Settings.Global.put",
            "ACTION_CALL",
            "SmsManager",
            "su ",
            "fastboot",
            "adb shell",
        ):
            self.assertNotIn(forbidden, source)

    def test_launcher_locales_have_exact_key_parity(self) -> None:
        expected = None
        for suffix in LOCALES:
            path = APP / f"res/values{suffix}/strings.xml"
            self.assertTrue(path.is_file(), path)
            root = ET.parse(path).getroot()
            keys = {node.attrib["name"] for node in root.findall("string")}
            self.assertEqual(len(keys), len(root.findall("string")))
            if expected is None:
                expected = keys
            else:
                self.assertEqual(keys, expected, path)
        self.assertEqual(
            expected,
            {
                "app_name",
                "launcher_title",
                "launcher_subtitle",
                "setup_title",
                "setup_body",
                "language_region",
                "privacy",
                "security",
                "finish_setup",
                "setup_done",
                "essentials",
                "settings",
                "files",
                "update",
                "apps",
                "unknown_app",
                "no_apps",
                "open_failed",
            },
        )

    def test_exact_stage_fragment_covers_every_launcher_source_file(self) -> None:
        manifest = json.loads(STAGE.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), 1)
        entries = manifest.get("files")
        self.assertIsInstance(entries, list)
        staged_sources = {entry["source"] for entry in entries}
        actual_sources = {
            path.relative_to(APP.parent.parent).as_posix()
            for path in APP.rglob("*")
            if path.is_file()
        }
        self.assertEqual(staged_sources, actual_sources)
        self.assertEqual(len(entries), len(staged_sources))
        for entry in entries:
            self.assertEqual(
                entry["destination"],
                "vendor/swir/" + entry["source"],
            )


if __name__ == "__main__":
    unittest.main()
