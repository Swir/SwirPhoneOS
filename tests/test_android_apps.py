from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.android_apps import AndroidAppSourceError, public_android_app_source_summary, validate_android_app_sources


class AndroidAppSourceTests(unittest.TestCase):
    def test_repository_source_apps_are_complete_but_not_runtime_claimed(self):
        summary = public_android_app_source_summary(validate_android_app_sources())
        self.assertEqual(summary["status"], "SOURCE_READY_NOT_BUILT")
        self.assertEqual(set(summary["source_ready_apps"]), {"calculator","settings","files","device_care","update","privacy","clock","notes","calendar","gallery","recorder","contacts","apps","swirroot"})
        self.assertEqual(summary["source_ready_count"], 14)
        self.assertEqual(summary["localized_catalogs"], 112)
        for capability in ("basic_math","system_settings","search","device_status","browse","copy_move_rename","share","safe_delete","storage_status","battery_status","thermal_status","hardware_diagnostics","channel_status","signed_metadata","permission_review","alarms","timers","stopwatch","world_clock","offline_notes","export","local_calendar","local_media","audio_recording","microphone_state","file_export","local_contacts","import_export","provider_bridge","package_catalog","signature_provenance","root_state","authorization_audit"):
            self.assertIn(capability, summary["implemented_capabilities"])
        self.assertEqual(summary["remaining_target_capabilities"], ["access_history","albums","guided_enable","guided_unroot","privacy_indicators","provider_bridge","recovery_handoff","scientific_math","staged_update_state","update_status"])
        self.assertIn("calendar:provider_bridge", summary["remaining_app_capabilities"])
        self.assertIn("apps:update_status", summary["remaining_app_capabilities"])
        self.assertNotIn("contacts:provider_bridge", summary["remaining_app_capabilities"])
        self.assertFalse(summary["android_build_verified"]); self.assertFalse(summary["runtime_verified"]); self.assertFalse(summary["device_write_allowed"])

    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name); product = root / "product"
        shutil.copytree(Path("platform/aosp_product"), product)
        registry = root / "manifest.json"; shutil.copy2(Path("system_apps/manifest.json"), registry)
        return temp, product, registry

    def test_permission_request_is_rejected_for_permission_free_app(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            manifest = product / "apps/SwirSettings/AndroidManifest.xml"; manifest.write_text(manifest.read_text(encoding="utf-8").replace("<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application', 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_gallery_permission_allowlist_is_exact(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            manifest = product / "apps/SwirGallery/AndroidManifest.xml"; manifest.write_text(manifest.read_text(encoding="utf-8").replace('android.permission.READ_MEDIA_VIDEO', 'android.permission.READ_MEDIA_AUDIO', 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_recorder_cannot_gain_network_permission(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            manifest = product / "apps/SwirRecorder/AndroidManifest.xml"; manifest.write_text(manifest.read_text(encoding="utf-8").replace("<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application', 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_contacts_permission_allowlist_is_exact(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            manifest = product / "apps/SwirContacts/AndroidManifest.xml"; manifest.write_text(manifest.read_text(encoding="utf-8").replace("<application", '<uses-permission android:name="android.permission.WRITE_CONTACTS"/>\n    <application', 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_contacts_must_keep_explicit_vcard_flow(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirContacts/src/org/swir/phoneos/contacts/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("ContactsContract.Contacts.CONTENT_VCARD_URI", "ContactsContract.Contacts.CONTENT_URI", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_apps_must_keep_signature_provenance(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirApps/src/org/swir/phoneos/apps/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("PackageManager.GET_SIGNING_CERTIFICATES", "0", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_broad_storage_permission_primitive_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8") + "\n// MANAGE_EXTERNAL_STORAGE\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_missing_locale_key_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirDeviceCare/res/values-de/strings.xml"; strings.write_text(strings.read_text(encoding="utf-8").replace('<string name="refresh">Aktualisieren</string>', ""), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_registry_must_not_claim_android_runtime(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            data = json.loads(registry.read_text(encoding="utf-8")); next(app for app in data["apps"] if app["id"] == "settings")["status"] = "ANDROID_RUNTIME"; registry.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_unreviewed_settings_action_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            catalog = product / "apps/SwirSettings/src/org/swir/phoneos/settings/SettingsCatalog.java"; catalog.write_text(catalog.read_text(encoding="utf-8").replace("android.settings.WIFI_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_files_must_keep_user_granted_tree_workflow(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("Intent.ACTION_OPEN_DOCUMENT_TREE", "Intent.ACTION_OPEN_DOCUMENT", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_device_care_must_keep_real_thermal_state(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirDeviceCare/src/org/swir/phoneos/device_care/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("getCurrentThermalStatus()", "hashCode()", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_update_must_keep_signature_verification(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            policy = product / "apps/SwirUpdate/src/org/swir/phoneos/update/UpdatePolicy.java"; policy.write_text(policy.read_text(encoding="utf-8").replace("SHA256withRSA", "NONEwithRSA", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_update_must_not_gain_install_path_in_source_stage(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirUpdate/src/org/swir/phoneos/update/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8") + "\n// RecoverySystem.installPackage\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_unreviewed_privacy_action_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            catalog = product / "apps/SwirPrivacy/src/org/swir/phoneos/privacy/PrivacyCatalog.java"; catalog.write_text(catalog.read_text(encoding="utf-8").replace("android.settings.PRIVACY_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_clock_must_keep_user_visible_alarm_handoff(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirClock/src/org/swir/phoneos/clock/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("AlarmClock.ACTION_SET_ALARM", "Intent.ACTION_VIEW", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_gallery_must_keep_owner_confirmed_delete(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirGallery/src/org/swir/phoneos/gallery/MainActivity.java"; activity.write_text(activity.read_text(encoding="utf-8").replace("MediaStore.createDeleteRequest", "MediaStore.createWriteRequest", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_recorder_must_stop_when_leaving_foreground(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirRecorder/src/org/swir/phoneos/recorder/MainActivity.java"; source = activity.read_text(encoding="utf-8"); self.assertIn("if (recorder != null) stopRecording(false);", source); activity.write_text(source.replace("stopRecording(false)", "refreshControls()"), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_swirroot_service_cannot_gain_process_execution(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            service = product / "apps/SwirRoot/src/org/swir/phoneos/swirroot/SwirRootService.java"; service.write_text(service.read_text(encoding="utf-8") + "\n// Runtime.getRuntime\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_swirroot_source_must_keep_write_backend_disabled(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            service = product / "apps/SwirRoot/src/org/swir/phoneos/swirroot/SwirRootService.java"; service.write_text(service.read_text(encoding="utf-8").replace("WRITE_BACKEND_ENABLED = false", "WRITE_BACKEND_ENABLED = true", 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_duplicate_stage_destination_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            stage = product / "stage_manifest.json"; data = json.loads(stage.read_text(encoding="utf-8")); data["files"][1]["destination"] = data["files"][0]["destination"]; stage.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)


if __name__ == "__main__": unittest.main()
