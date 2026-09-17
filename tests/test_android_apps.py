from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.android_apps import AndroidAppSourceError, public_android_app_source_summary, validate_android_app_sources


SOURCE_APPS = {
    "phone", "contacts", "messages", "camera", "gallery", "files", "settings", "browser",
    "clock", "calculator", "notes", "recorder", "calendar", "weather", "update", "backup",
    "privacy", "device_care", "apps", "swirroot",
}


class AndroidAppSourceTests(unittest.TestCase):
    def test_repository_source_apps_are_complete_but_not_runtime_claimed(self):
        summary = public_android_app_source_summary(validate_android_app_sources())
        self.assertEqual(summary["status"], "SOURCE_READY_NOT_BUILT")
        self.assertEqual(set(summary["source_ready_apps"]), SOURCE_APPS)
        self.assertEqual(summary["source_ready_count"], 20)
        self.assertEqual(summary["localized_catalogs"], 160)
        for capability in (
            "dialer", "sms", "camera_capability_report", "basic_math", "system_settings", "search", "device_status",
            "browse", "copy_move_rename", "share", "safe_delete", "web_browsing", "privacy_controls", "storage_status",
            "battery_status", "thermal_status", "hardware_diagnostics", "channel_status", "signed_metadata", "permission_review",
            "alarms", "timers", "stopwatch", "world_clock", "offline_notes", "export", "local_calendar", "forecast",
            "provider_attribution", "unit_preferences", "local_media", "audio_recording", "microphone_state", "file_export",
            "local_contacts", "import_export", "provider_bridge", "supported_data_backup", "recovery_metadata",
            "package_catalog", "signature_provenance", "root_state", "authorization_audit",
        ):
            self.assertIn(capability, summary["implemented_capabilities"])
        self.assertEqual(summary["remaining_target_capabilities"], [
            "access_history", "albums", "conversation_history", "downloads", "guided_enable", "guided_unroot", "in_call",
            "mms", "photo_capture", "privacy_indicators", "provider_bridge", "recent_calls", "recovery_handoff",
            "restore_orchestration", "scientific_math", "staged_update_state", "update_status", "video_capture",
        ])
        for item in (
            "phone:in_call", "phone:recent_calls", "messages:mms", "messages:conversation_history",
            "camera:photo_capture", "camera:video_capture", "browser:downloads", "calendar:provider_bridge",
            "backup:restore_orchestration", "apps:update_status",
        ):
            self.assertIn(item, summary["remaining_app_capabilities"])
        for item in (
            "messages:sms", "camera:camera_capability_report", "browser:web_browsing", "browser:privacy_controls",
            "weather:forecast", "weather:provider_attribution", "weather:unit_preferences", "backup:supported_data_backup",
            "backup:recovery_metadata", "contacts:provider_bridge",
        ):
            self.assertNotIn(item, summary["remaining_app_capabilities"])
        self.assertFalse(summary["android_build_verified"])
        self.assertFalse(summary["runtime_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name); product = root / "product"
        shutil.copytree(Path("platform/aosp_product"), product)
        registry = root / "manifest.json"; shutil.copy2(Path("system_apps/manifest.json"), registry)
        return temp, product, registry

    def _replace_and_reject(self, relative: str, old: str, new: str):
        temp, product, registry = self._copy_fixture()
        with temp:
            path = product / relative
            source = path.read_text(encoding="utf-8")
            self.assertIn(old, source)
            path.write_text(source.replace(old, new, 1), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_permission_request_is_rejected_for_permission_free_app(self):
        self._replace_and_reject("apps/SwirSettings/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application')

    def test_phone_cannot_gain_direct_call_permission(self):
        self._replace_and_reject("apps/SwirPhone/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.CALL_PHONE"/>\n    <application')

    def test_phone_must_keep_user_visible_dial_handoff(self):
        self._replace_and_reject("apps/SwirPhone/src/org/swir/phoneos/phone/MainActivity.java", "Intent.ACTION_DIAL", "Intent.ACTION_CALL")

    def test_messages_cannot_gain_direct_sms_permission(self):
        self._replace_and_reject("apps/SwirMessages/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.SEND_SMS"/>\n    <application')

    def test_messages_must_keep_user_visible_sendto_handoff(self):
        self._replace_and_reject("apps/SwirMessages/src/org/swir/phoneos/messages/MainActivity.java", "Intent.ACTION_SENDTO", "Intent.ACTION_SEND")

    def test_camera_cannot_claim_direct_capture_before_hardware_validation(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirCamera/src/org/swir/phoneos/camera/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8") + "\n// openCamera(\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_browser_network_permission_allowlist_is_exact(self):
        self._replace_and_reject("apps/SwirBrowser/AndroidManifest.xml", "android.permission.INTERNET", "android.permission.ACCESS_FINE_LOCATION")

    def test_browser_must_keep_javascript_disabled_by_default(self):
        self._replace_and_reject("apps/SwirBrowser/src/org/swir/phoneos/browser/MainActivity.java", "setJavaScriptEnabled(false)", "setJavaScriptEnabled(true)")

    def test_weather_cannot_gain_location_permission(self):
        self._replace_and_reject("apps/SwirWeather/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n    <application')

    def test_weather_must_keep_reviewed_forecast_endpoint_policy(self):
        self._replace_and_reject("apps/SwirWeather/src/org/swir/phoneos/weather/MainActivity.java", "WeatherPolicy.forecastUrl", "WeatherPolicy.providerUrl")

    def test_backup_must_keep_safe_archive_inspection(self):
        self._replace_and_reject("apps/SwirBackup/src/org/swir/phoneos/backup/MainActivity.java", "Intent.EXTRA_ALLOW_MULTIPLE", "Intent.EXTRA_LOCAL_ONLY")

    def test_gallery_permission_allowlist_is_exact(self):
        self._replace_and_reject("apps/SwirGallery/AndroidManifest.xml", "android.permission.READ_MEDIA_VIDEO", "android.permission.READ_MEDIA_AUDIO")

    def test_recorder_cannot_gain_network_permission(self):
        self._replace_and_reject("apps/SwirRecorder/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application')

    def test_contacts_permission_allowlist_is_exact(self):
        self._replace_and_reject("apps/SwirContacts/AndroidManifest.xml", "<application", '<uses-permission android:name="android.permission.WRITE_CONTACTS"/>\n    <application')

    def test_contacts_must_keep_explicit_vcard_flow(self):
        self._replace_and_reject("apps/SwirContacts/src/org/swir/phoneos/contacts/MainActivity.java", "ContactsContract.Contacts.CONTENT_VCARD_URI", "ContactsContract.Contacts.CONTENT_URI")

    def test_apps_must_keep_signature_provenance(self):
        self._replace_and_reject("apps/SwirApps/src/org/swir/phoneos/apps/MainActivity.java", "PackageManager.GET_SIGNING_CERTIFICATES", "0")

    def test_broad_storage_permission_primitive_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8") + "\n// MANAGE_EXTERNAL_STORAGE\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_missing_locale_key_is_rejected(self):
        self._replace_and_reject("apps/SwirDeviceCare/res/values-de/strings.xml", '<string name="refresh">Aktualisieren</string>', "")

    def test_registry_must_not_claim_android_runtime(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            data = json.loads(registry.read_text(encoding="utf-8")); next(app for app in data["apps"] if app["id"] == "settings")["status"] = "ANDROID_RUNTIME"; registry.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_unreviewed_settings_action_is_rejected(self):
        self._replace_and_reject("apps/SwirSettings/src/org/swir/phoneos/settings/SettingsCatalog.java", "android.settings.WIFI_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES")

    def test_files_must_keep_user_granted_tree_workflow(self):
        self._replace_and_reject("apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java", "Intent.ACTION_OPEN_DOCUMENT_TREE", "Intent.ACTION_OPEN_DOCUMENT")

    def test_device_care_must_keep_real_thermal_state(self):
        self._replace_and_reject("apps/SwirDeviceCare/src/org/swir/phoneos/device_care/MainActivity.java", "getCurrentThermalStatus()", "hashCode()")

    def test_update_must_keep_signature_verification(self):
        self._replace_and_reject("apps/SwirUpdate/src/org/swir/phoneos/update/UpdatePolicy.java", "SHA256withRSA", "NONEwithRSA")

    def test_update_must_not_gain_install_path_in_source_stage(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirUpdate/src/org/swir/phoneos/update/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8") + "\n// RecoverySystem.installPackage\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)

    def test_unreviewed_privacy_action_is_rejected(self):
        self._replace_and_reject("apps/SwirPrivacy/src/org/swir/phoneos/privacy/PrivacyCatalog.java", "android.settings.PRIVACY_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES")

    def test_clock_must_keep_user_visible_alarm_handoff(self):
        self._replace_and_reject("apps/SwirClock/src/org/swir/phoneos/clock/MainActivity.java", "AlarmClock.ACTION_SET_ALARM", "Intent.ACTION_VIEW")

    def test_gallery_must_keep_owner_confirmed_delete(self):
        self._replace_and_reject("apps/SwirGallery/src/org/swir/phoneos/gallery/MainActivity.java", "MediaStore.createDeleteRequest", "MediaStore.createWriteRequest")

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
        self._replace_and_reject("apps/SwirRoot/src/org/swir/phoneos/swirroot/SwirRootService.java", "WRITE_BACKEND_ENABLED = false", "WRITE_BACKEND_ENABLED = true")

    def test_duplicate_stage_destination_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            stage = product / "stage_manifest.json"; data = json.loads(stage.read_text(encoding="utf-8")); data["files"][1]["destination"] = data["files"][0]["destination"]; stage.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError): validate_android_app_sources(product, registry)


if __name__ == "__main__": unittest.main()
