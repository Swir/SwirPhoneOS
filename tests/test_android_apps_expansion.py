from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.android_apps import AndroidAppSourceError, public_android_app_source_summary, validate_android_app_sources


class AndroidAppExpansionTests(unittest.TestCase):
    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name); product = root / "product"
        shutil.copytree(Path("platform/aosp_product"), product)
        registry = root / "manifest.json"; shutil.copy2(Path("system_apps/manifest.json"), registry)
        return temp, product, registry

    def test_expanded_apps_are_reviewed_source_not_runtime(self):
        summary = public_android_app_source_summary(validate_android_app_sources())
        self.assertEqual(summary["source_ready_count"], 15)
        self.assertEqual(summary["localized_catalogs"], 120)
        for app_id in ("phone", "notes", "calendar", "gallery", "recorder", "contacts", "apps", "swirroot"): self.assertIn(app_id, summary["source_ready_apps"])
        for capability in ("dialer", "offline_notes", "local_calendar", "local_media", "audio_recording", "microphone_state", "file_export", "local_contacts", "import_export", "package_catalog", "signature_provenance", "root_state", "authorization_audit"): self.assertIn(capability, summary["implemented_capabilities"])
        for capability in ("in_call", "recent_calls", "albums", "provider_bridge", "update_status", "guided_enable", "guided_unroot"): self.assertIn(capability, summary["remaining_target_capabilities"])
        self.assertIn("phone:in_call", summary["remaining_app_capabilities"])
        self.assertIn("phone:recent_calls", summary["remaining_app_capabilities"])
        self.assertIn("calendar:provider_bridge", summary["remaining_app_capabilities"])
        self.assertIn("apps:update_status", summary["remaining_app_capabilities"])
        self.assertFalse(summary["android_build_verified"]); self.assertFalse(summary["runtime_verified"])

    def test_notes_must_keep_explicit_document_export(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirNotes/src/org/swir/phoneos/notes/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8").replace("Intent.ACTION_CREATE_DOCUMENT", "Intent.ACTION_VIEW", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_calendar_provider_is_not_claimed_before_review(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirCalendar/src/org/swir/phoneos/calendar/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8") + "\n// CalendarContract\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_stage_fragment_duplicate_is_rejected_across_manifests(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            fragment = product / "stage_manifest.d/media-capture.json"; data = json.loads(fragment.read_text(encoding="utf-8")); data["files"][0]["destination"] = "vendor/swir/apps/SwirCalculator/Android.bp"
            fragment.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)


if __name__ == "__main__": unittest.main()
