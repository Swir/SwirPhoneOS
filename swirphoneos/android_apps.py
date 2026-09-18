"""Fail-closed source validation for first-party Android apps staged into AOSP."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .stage_manifest import StageManifestError, load_stage_files
from .system_apps import SystemAppRegistry, load_registry


class AndroidAppSourceError(ValueError):
    """Raised when checked-in Android application source overclaims or is unsafe/incomplete."""


@dataclass(frozen=True)
class AndroidAppSourceSummary:
    source_ready_apps: tuple[str, ...]
    localized_catalogs: int
    source_files: int
    target_capabilities: tuple[str, ...]
    implemented_capabilities: tuple[str, ...]
    missing_app_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class _AppSpec:
    app_id: str
    folder: str
    module: str
    java_package: str
    logic_file: str
    activity_file: str
    host_test: str
    icon_file: str
    implemented_capabilities: tuple[str, ...]
    allowed_permissions: tuple[str, ...] = ()


_LOCALES = ("en", "pl", "nb", "de", "es", "fr", "pt", "ar")
_RESOURCE_DIR = {"en":"values","pl":"values-pl","nb":"values-nb","de":"values-de","es":"values-es","fr":"values-fr","pt":"values-pt","ar":"values-ar"}
_MAX_TEXT = 1_000_000
_SPECS = {
    "phone": _AppSpec("phone","SwirPhone","SwirPhone","org.swir.phoneos.phone","src/org/swir/phoneos/phone/DialerPolicy.java","src/org/swir/phoneos/phone/MainActivity.java","hosttest/DialerPolicyHostTest.java","res/drawable/ic_phone.xml",("dialer","in_call","recent_calls"),("android.permission.READ_CALL_LOG",)),
    "messages": _AppSpec("messages","SwirMessages","SwirMessages","org.swir.phoneos.messages","src/org/swir/phoneos/messages/MessagePolicy.java","src/org/swir/phoneos/messages/MainActivity.java","hosttest/MessagePolicyHostTest.java","res/drawable/ic_messages.xml",("sms",)),
    "camera": _AppSpec("camera","SwirCamera","SwirCamera","org.swir.phoneos.camera","src/org/swir/phoneos/camera/CameraPolicy.java","src/org/swir/phoneos/camera/MainActivity.java","hosttest/CameraPolicyHostTest.java","res/drawable/ic_camera.xml",("camera_capability_report",)),
    "calculator": _AppSpec("calculator","SwirCalculator","SwirCalculator","org.swir.phoneos.calculator","src/org/swir/phoneos/calculator/CalculatorEngine.java","src/org/swir/phoneos/calculator/MainActivity.java","hosttest/CalculatorEngineHostTest.java","res/drawable/ic_calculator.xml",("basic_math",)),
    "settings": _AppSpec("settings","SwirSettings","SwirSettings","org.swir.phoneos.settings","src/org/swir/phoneos/settings/SettingsCatalog.java","src/org/swir/phoneos/settings/MainActivity.java","hosttest/SettingsCatalogHostTest.java","res/drawable/ic_settings.xml",("system_settings","search","device_status")),
    "files": _AppSpec("files","SwirFiles","SwirFiles","org.swir.phoneos.files","src/org/swir/phoneos/files/FilePolicy.java","src/org/swir/phoneos/files/MainActivity.java","hosttest/FilePolicyHostTest.java","res/drawable/ic_files.xml",("browse","search","copy_move_rename","share","safe_delete")),
    "browser": _AppSpec("browser","SwirBrowser","SwirBrowser","org.swir.phoneos.browser","src/org/swir/phoneos/browser/BrowserPolicy.java","src/org/swir/phoneos/browser/MainActivity.java","hosttest/BrowserPolicyHostTest.java","res/drawable/ic_browser.xml",("web_browsing","downloads","privacy_controls"),("android.permission.INTERNET",)),
    "device_care": _AppSpec("device_care","SwirDeviceCare","SwirDeviceCare","org.swir.phoneos.device_care","src/org/swir/phoneos/device_care/HealthModel.java","src/org/swir/phoneos/device_care/MainActivity.java","hosttest/HealthModelHostTest.java","res/drawable/ic_device_care.xml",("storage_status","battery_status","thermal_status","hardware_diagnostics")),
    "update": _AppSpec("update","SwirUpdate","SwirUpdate","org.swir.phoneos.update","src/org/swir/phoneos/update/UpdatePolicy.java","src/org/swir/phoneos/update/MainActivity.java","hosttest/UpdatePolicyHostTest.java","res/drawable/ic_update.xml",("channel_status","signed_metadata")),
    "privacy": _AppSpec("privacy","SwirPrivacy","SwirPrivacy","org.swir.phoneos.privacy","src/org/swir/phoneos/privacy/PrivacyCatalog.java","src/org/swir/phoneos/privacy/MainActivity.java","hosttest/PrivacyCatalogHostTest.java","res/drawable/ic_privacy.xml",("permission_review",)),
    "clock": _AppSpec("clock","SwirClock","SwirClock","org.swir.phoneos.clock","src/org/swir/phoneos/clock/ClockCore.java","src/org/swir/phoneos/clock/MainActivity.java","hosttest/ClockCoreHostTest.java","res/drawable/ic_clock.xml",("alarms","timers","stopwatch","world_clock")),
    "notes": _AppSpec("notes","SwirNotes","SwirNotes","org.swir.phoneos.notes","src/org/swir/phoneos/notes/NotePolicy.java","src/org/swir/phoneos/notes/MainActivity.java","hosttest/NotePolicyHostTest.java","res/drawable/ic_notes.xml",("offline_notes","export","share")),
    "calendar": _AppSpec("calendar","SwirCalendar","SwirCalendar","org.swir.phoneos.calendar","src/org/swir/phoneos/calendar/EventPolicy.java","src/org/swir/phoneos/calendar/MainActivity.java","hosttest/EventPolicyHostTest.java","res/drawable/ic_calendar.xml",("local_calendar","provider_bridge")),
    "weather": _AppSpec("weather","SwirWeather","SwirWeather","org.swir.phoneos.weather","src/org/swir/phoneos/weather/WeatherPolicy.java","src/org/swir/phoneos/weather/MainActivity.java","hosttest/WeatherPolicyHostTest.java","res/drawable/ic_weather.xml",("forecast","provider_attribution","unit_preferences"),("android.permission.INTERNET",)),
    "gallery": _AppSpec("gallery","SwirGallery","SwirGallery","org.swir.phoneos.gallery","src/org/swir/phoneos/gallery/MediaPolicy.java","src/org/swir/phoneos/gallery/MainActivity.java","hosttest/MediaPolicyHostTest.java","res/drawable/ic_gallery.xml",("local_media","share","safe_delete"),("android.permission.READ_MEDIA_IMAGES","android.permission.READ_MEDIA_VIDEO")),
    "recorder": _AppSpec("recorder","SwirRecorder","SwirRecorder","org.swir.phoneos.recorder","src/org/swir/phoneos/recorder/RecorderPolicy.java","src/org/swir/phoneos/recorder/MainActivity.java","hosttest/RecorderPolicyHostTest.java","res/drawable/ic_recorder.xml",("audio_recording","microphone_state","file_export"),("android.permission.RECORD_AUDIO",)),
    "contacts": _AppSpec("contacts","SwirContacts","SwirContacts","org.swir.phoneos.contacts","src/org/swir/phoneos/contacts/ContactPolicy.java","src/org/swir/phoneos/contacts/MainActivity.java","hosttest/ContactPolicyHostTest.java","res/drawable/ic_contacts.xml",("local_contacts","import_export","provider_bridge"),("android.permission.READ_CONTACTS",)),
    "backup": _AppSpec("backup","SwirBackup","SwirBackup","org.swir.phoneos.backup","src/org/swir/phoneos/backup/BackupPolicy.java","src/org/swir/phoneos/backup/MainActivity.java","hosttest/BackupPolicyHostTest.java","res/drawable/ic_backup.xml",("supported_data_backup","recovery_metadata")),
    "apps": _AppSpec("apps","SwirApps","SwirApps","org.swir.phoneos.apps","src/org/swir/phoneos/apps/AppCatalogPolicy.java","src/org/swir/phoneos/apps/MainActivity.java","hosttest/AppCatalogPolicyHostTest.java","res/drawable/ic_apps.xml",("package_catalog","signature_provenance")),
    "swirroot": _AppSpec("swirroot","SwirRoot","SwirRoot","org.swir.phoneos.swirroot","src/org/swir/phoneos/swirroot/RootPolicy.java","src/org/swir/phoneos/swirroot/MainActivity.java","hosttest/RootPolicyHostTest.java","res/drawable/ic_swirroot.xml",("root_state","authorization_audit")),
}
_SETTINGS_ACTIONS = frozenset({"android.settings.WIFI_SETTINGS","android.settings.BLUETOOTH_SETTINGS","android.settings.DISPLAY_SETTINGS","android.settings.SOUND_SETTINGS","android.settings.SECURITY_SETTINGS","android.settings.PRIVACY_SETTINGS","android.settings.ACCESSIBILITY_SETTINGS","android.settings.LOCALE_SETTINGS","android.settings.INTERNAL_STORAGE_SETTINGS","android.settings.APPLICATION_SETTINGS"})
_PRIVACY_ACTIONS = frozenset({"android.settings.PRIVACY_SETTINGS","android.settings.MANAGE_PERMISSIONS","android.settings.LOCATION_SOURCE_SETTINGS","android.settings.APPLICATION_SETTINGS","android.settings.MANAGE_SPECIAL_APP_ACCESSES"})
_NETWORK_APPS = frozenset({"browser", "weather"})


def _read(path: Path) -> str:
    if not path.is_file() or path.is_symlink(): raise AndroidAppSourceError(f"Missing or unsafe Android source file: {path.name}")
    try: text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc: raise AndroidAppSourceError("Android app source must be readable strict UTF-8.") from exc
    if not text or len(text) > _MAX_TEXT: raise AndroidAppSourceError("Android app source file has an invalid size.")
    return text


def _string_keys(path: Path) -> set[str]:
    try: root = ET.fromstring(_read(path))
    except ET.ParseError as exc: raise AndroidAppSourceError("Android string resources are malformed XML.") from exc
    if root.tag != "resources": raise AndroidAppSourceError("Android string resource root must be <resources>.")
    keys: set[str] = set()
    for item in root.findall("string"):
        name=(item.get("name") or "").strip()
        if not name or name in keys: raise AndroidAppSourceError("Android string resources contain missing/duplicate names.")
        keys.add(name)
    if not keys: raise AndroidAppSourceError("Android app must contain localizable strings.")
    return keys


def _load_stage_sources(product_root: Path) -> set[str]:
    try: files=load_stage_files(product_root)
    except StageManifestError as exc: raise AndroidAppSourceError(str(exc)) from exc
    if not files: raise AndroidAppSourceError("AOSP stage manifest has no files.")
    return {item.source.as_posix() for item in files}


def _validate_common(product_root: Path, product_mk: str, app, spec: _AppSpec, staged: set[str]) -> tuple[int,int,str,str,str]:
    app_root=product_root/"apps"/spec.folder
    bp=_read(app_root/"Android.bp"); manifest_text=_read(app_root/"AndroidManifest.xml"); logic=_read(app_root/spec.logic_file); activity=_read(app_root/spec.activity_file)
    _read(app_root/spec.icon_file); _read(app_root/spec.host_test)
    required_bp=("android_app {",f'name: "{spec.module}"','srcs: ["src/**/*.java"]','resource_dirs: ["res"]','sdk_version: "current"','product_specific: true')
    if any(token not in bp for token in required_bp): raise AndroidAppSourceError(f"{spec.module} Android.bp does not match the source contract.")
    if "PRODUCT_PACKAGES" not in product_mk or spec.module not in product_mk: raise AndroidAppSourceError(f"{spec.module} is not included in the Cuttlefish product.")
    try: manifest=ET.fromstring(manifest_text)
    except ET.ParseError as exc: raise AndroidAppSourceError(f"{spec.module} manifest is malformed XML.") from exc
    if manifest.tag!="manifest" or manifest.get("package")!=app.package: raise AndroidAppSourceError(f"{spec.module} package identity does not match the registry.")
    if app.package!=spec.java_package: raise AndroidAppSourceError(f"{spec.module} registry package drifted from its source contract.")
    ns="{http://schemas.android.com/apk/res/android}"; permission_nodes=manifest.findall("uses-permission"); permission_names=[(node.get(ns+"name") or "").strip() for node in permission_nodes]
    if any(not name for name in permission_names) or len(permission_names)!=len(set(permission_names)): raise AndroidAppSourceError(f"{spec.module} manifest permissions must be unique and named.")
    if any(set(node.attrib)!={ns+"name"} for node in permission_nodes): raise AndroidAppSourceError(f"{spec.module} permission declarations must not carry unreviewed attributes.")
    if frozenset(permission_names)!=frozenset(spec.allowed_permissions): raise AndroidAppSourceError(f"{spec.module} manifest permissions do not match the reviewed least-privilege allowlist.")
    application=manifest.find("application")
    if application is None or application.get(ns+"supportsRtl")!="true" or application.get(ns+"allowBackup")!="false": raise AndroidAppSourceError(f"{spec.module} manifest must be RTL-aware and backup-disabled.")
    package_line=f"package {spec.java_package};"
    if package_line not in logic or package_line not in activity: raise AndroidAppSourceError(f"{spec.module} Java package identity drifted.")
    if re.search(r"^\s*import\s+android\.",logic,flags=re.MULTILINE): raise AndroidAppSourceError(f"{spec.module} host-testable logic must remain pure Java.")
    java_files=sorted(path for path in app_root.rglob("*.java") if path.is_file() and "hosttest" not in path.parts)
    if not java_files: raise AndroidAppSourceError(f"{spec.module} has no Android Java source.")
    java_bundle="\n".join(_read(path) for path in java_files)
    forbidden=("Runtime.getRuntime","ProcessBuilder",'"su"',"DexClassLoader","System.loadLibrary","MANAGE_EXTERNAL_STORAGE","READ_EXTERNAL_STORAGE","WRITE_EXTERNAL_STORAGE")
    if any(token in java_bundle or token in manifest_text for token in forbidden): raise AndroidAppSourceError(f"{spec.module} source contains a forbidden execution/storage primitive.")
    network_tokens=("java.net.","javax.net.","android.webkit.","loadUrl(")
    if spec.app_id not in _NETWORK_APPS and any(token in java_bundle for token in network_tokens): raise AndroidAppSourceError(f"{spec.module} source contains an unreviewed network primitive.")
    if spec.app_id not in _NETWORK_APPS and "android.permission.INTERNET" in manifest_text: raise AndroidAppSourceError(f"{spec.module} may not request network access.")
    english=_string_keys(app_root/"res/values/strings.xml"); localized=0
    for locale in _LOCALES:
        if _string_keys(app_root/"res"/_RESOURCE_DIR[locale]/"strings.xml")!=english: raise AndroidAppSourceError(f"{spec.module} localization keys drifted for {locale}.")
        localized+=1
    required_stage={path.relative_to(product_root).as_posix() for path in app_root.rglob("*") if path.is_file() and "hosttest" not in path.parts}
    missing=sorted(required_stage-staged)
    if missing: raise AndroidAppSourceError(f"{spec.module} source is not fully staged: {missing}")
    return localized,len(required_stage),logic,activity,java_bundle


def _validate_phone(logic,activity):
    if any(x not in logic for x in ("MAX_DIAL_LENGTH","normalize","isDialable","appendKey","eraseLast","Character.isDigit")): raise AndroidAppSourceError("SwirPhone host-tested dial policy drifted.")
    required=("Intent.ACTION_DIAL",'Uri.fromParts("tel"',"resolveActivity(getPackageManager())","startActivity(intent)","DialerPolicy.normalize","R.array.dial_keys","RoleManager.ROLE_DIALER","Manifest.permission.READ_CALL_LOG","checkSelfPermission(Manifest.permission.READ_CALL_LOG)","requestPermissions(new String[]{Manifest.permission.READ_CALL_LOG}","CallLog.Calls.CONTENT_URI","CallLog.Calls.NUMBER_PRESENTATION","TelecomManager.PRESENTATION_ALLOWED","CallHistoryPolicy.MAX_RECENT_CALLS","getContentResolver().query")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirPhone must retain explicit owner-visible dialing plus default-role-gated read-only recent-call history.")
    forbidden=("Intent.ACTION_CALL","TelecomManager.placeCall","Manifest.permission.CALL_PHONE","Manifest.permission.WRITE_CALL_LOG","getContentResolver().insert","getContentResolver().update","getContentResolver().delete")
    if any(x in activity for x in forbidden): raise AndroidAppSourceError("SwirPhone must not directly place calls or mutate call history.")

def _validate_messages(logic,activity):
    if any(x not in logic for x in ("MAX_RECIPIENTS","MAX_BODY_LENGTH","normalizeRecipients","normalizeRecipient","normalizeBody","canHandoff","remainingCharacters","Character.isDigit")): raise AndroidAppSourceError("SwirMessages host-tested compose policy drifted.")
    required=("Intent.ACTION_SENDTO",'Uri.fromParts("smsto"','putExtra("sms_body"',"resolveActivity(getPackageManager())","startActivity(intent)","getSharedPreferences","MessagePolicy.canHandoff")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirMessages must retain local draft persistence and explicit user-visible system messaging handoff.")
    forbidden=("SmsManager","sendTextMessage","sendMultipartTextMessage","Telephony.Sms","Manifest.permission.SEND_SMS","Manifest.permission.READ_SMS","Manifest.permission.RECEIVE_SMS")
    if any(x in activity or x in logic for x in forbidden): raise AndroidAppSourceError("SwirMessages source stage must not silently send/read SMS or claim conversation history.")

def _validate_camera(logic,activity):
    if any(x not in logic for x in ("validDimensions","megapixels","formatMegapixels","lensLabel")): raise AndroidAppSourceError("SwirCamera host-tested capability policy drifted.")
    required=("CameraManager","getCameraIdList","CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP","getOutputSizes(ImageFormat.JPEG)","MediaStore.ACTION_IMAGE_CAPTURE","MediaStore.ACTION_VIDEO_CAPTURE","CameraPolicy.formatMegapixels")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirCamera must retain capability reporting and owner-visible capture hand-off.")
    if any(x in activity for x in ("openCamera(","CameraDevice","MediaRecorder","ImageReader.newInstance")): raise AndroidAppSourceError("SwirCamera source stage must not claim direct photo/video capture before hardware validation.")

def _validate_calculator(logic,activity):
    if "java.math.BigDecimal" not in logic or "equalsResult" not in logic: raise AndroidAppSourceError("SwirCalculator must retain its host-tested decimal engine.")
    if "DecimalFormatSymbols" not in activity: raise AndroidAppSourceError("SwirCalculator must preserve locale-aware decimal display.")
def _validate_settings(logic,activity):
    if frozenset(re.findall(r'"(android\.settings\.[A-Z_]+)"',logic))!=_SETTINGS_ACTIONS: raise AndroidAppSourceError("SwirSettings routes must match the reviewed public-settings allowlist exactly.")
    if any(x not in activity for x in ("Build.MODEL","Build.VERSION.RELEASE","Build.VERSION.SDK_INT","startActivity(new Intent(entry.action()))")): raise AndroidAppSourceError("SwirSettings must expose real device state and reviewed routes.")
def _validate_files(logic,activity):
    required=("Intent.ACTION_OPEN_DOCUMENT_TREE","takePersistableUriPermission","DocumentsContract.buildChildDocumentsUriUsingTree","DocumentsContract.createDocument","DocumentsContract.renameDocument","DocumentsContract.copyDocument","DocumentsContract.moveDocument","DocumentsContract.deleteDocument","Intent.FLAG_GRANT_READ_URI_PERMISSION","Intent.FLAG_GRANT_WRITE_URI_PERMISSION")
    if any(x not in activity for x in required) or "validName" not in logic or "Character.isISOControl" not in logic: raise AndroidAppSourceError("SwirFiles must retain its reviewed user-granted SAF workflow and file policy.")
def _validate_browser(logic,activity):
    policy_required=("MAX_URL_LENGTH","MAX_QUERY_LENGTH","MAX_DOWNLOAD_FILENAME_LENGTH","MAX_MIME_TYPE_LENGTH","normalizeUrl","searchUrl","isSafeUrl","isSafeDownloadUrl","safeDownloadFileName","safeMimeType","URI")
    if any(x not in logic for x in policy_required): raise AndroidAppSourceError("SwirBrowser host-tested URL/download policy drifted.")
    required=("WebView","setJavaScriptEnabled(false)","setAllowFileAccess(false)","setAllowContentAccess(false)","MIXED_CONTENT_NEVER_ALLOW","setSafeBrowsingEnabled(true)","setAcceptThirdPartyCookies(webView, false)","shouldOverrideUrlLoading","BrowserPolicy.normalizeUrl","removeAllCookies","DownloadManager","setDownloadListener","BrowserPolicy.isSafeDownloadUrl","BrowserPolicy.safeDownloadFileName","BrowserPolicy.safeMimeType","setDestinationInExternalFilesDir","Environment.DIRECTORY_DOWNLOADS","DownloadManager.ACTION_VIEW_DOWNLOADS")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirBrowser must retain HTTPS-first browsing, conservative privacy defaults and app-scoped owner-visible downloads.")
    forbidden=("getCookie(","setDestinationInExternalPublicDir","setDestinationUri(")
    if any(x in activity for x in forbidden): raise AndroidAppSourceError("SwirBrowser downloads must not copy WebView cookies or escape the reviewed app-scoped destination.")
def _validate_device_care(logic,activity):
    required=("Build.VERSION.SECURITY_PATCH","BatteryManager","StatFs","ActivityManager.MemoryInfo","getCurrentThermalStatus","Formatter.formatFileSize")
    if any(x not in activity for x in required) or any(x not in logic for x in ("percentUsed","thermalBand","batteryLevelValid")): raise AndroidAppSourceError("SwirDeviceCare must retain real framework health state and calculations.")
def _validate_update(logic,activity):
    if any(x not in logic for x in ("SHA256withRSA",'MessageDigest.getInstance("SHA-256")',"channelForBuild","fingerprintMatches")) or any(x not in activity for x in ("Build.FINGERPRINT","Build.TYPE","Build.TAGS","Settings.ACTION_SYSTEM_UPDATE_SETTINGS")): raise AndroidAppSourceError("SwirUpdate verification/build-state contract drifted.")
    if "DownloadManager" in activity or "RecoverySystem.installPackage" in activity: raise AndroidAppSourceError("SwirUpdate source stage must not download or install update packages.")
def _validate_privacy(logic,activity):
    if frozenset(re.findall(r'"(android\.settings\.[A-Z_]+)"',logic))!=_PRIVACY_ACTIONS: raise AndroidAppSourceError("SwirPrivacy routes must match the reviewed privacy-settings allowlist exactly.")
    if any(x not in activity for x in ("PrivacyCatalog.search","resolveActivity(getPackageManager())","startActivity(intent)")): raise AndroidAppSourceError("SwirPrivacy must use reviewed Android settings surfaces.")
def _validate_clock(logic,activity):
    if any(x not in logic for x in ("timerMillis","validAlarmTime","stopwatchElapsed","timerRemaining","worldTime")) or any(x not in activity for x in ("SystemClock.elapsedRealtime","AlarmClock.ACTION_SET_ALARM","AlarmClock.EXTRA_HOUR","AlarmClock.EXTRA_MINUTES","AlarmClock.EXTRA_SKIP_UI, false","ClockCore.timerRemaining","ClockCore.stopwatchElapsed","ClockCore.worldTime")): raise AndroidAppSourceError("SwirClock daily clock contract drifted.")
def _validate_notes(logic,activity):
    if any(x not in logic for x in ("validNote","matches","safeExportBase","exportMarkdown","MAX_BODY")): raise AndroidAppSourceError("SwirNotes host-tested note policy drifted.")
    if any(x not in activity for x in ("SQLiteOpenHelper","Intent.ACTION_CREATE_DOCUMENT","Intent.ACTION_SEND","openOutputStream","NotePolicy.exportMarkdown")): raise AndroidAppSourceError("SwirNotes must retain local CRUD plus explicit share/export workflows.")
def _validate_calendar(logic,activity):
    policy_required=("normalizeEnd","matches","escapeIcs","unescapeIcs","toIcs","parseSingleEvent","MAX_ICS_BYTES","BEGIN:VCALENDAR")
    if any(x not in logic for x in policy_required): raise AndroidAppSourceError("SwirCalendar event/ICS policy drifted.")
    required=("SQLiteOpenHelper","DatePickerDialog","TimePickerDialog","Intent.ACTION_CREATE_DOCUMENT","Intent.ACTION_OPEN_DOCUMENT","Intent.CATEGORY_OPENABLE","Intent.ACTION_SEND","Intent.ACTION_INSERT","CalendarContract.Events.CONTENT_URI","CalendarContract.Events.TITLE","CalendarContract.Events.EVENT_LOCATION","CalendarContract.EXTRA_EVENT_BEGIN_TIME","CalendarContract.EXTRA_EVENT_END_TIME","resolveActivity(getPackageManager())","EventPolicy.toIcs","EventPolicy.parseSingleEvent","CodingErrorAction.REPORT","EventPolicy.MAX_ICS_BYTES")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirCalendar must retain local-first import/export plus owner-visible device-calendar hand-off.")
    forbidden=("Manifest.permission.READ_CALENDAR","Manifest.permission.WRITE_CALENDAR","getContentResolver().insert(CalendarContract.Events.CONTENT_URI","getContentResolver().update(CalendarContract.Events.CONTENT_URI","getContentResolver().delete(CalendarContract.Events.CONTENT_URI")
    if any(x in activity for x in forbidden): raise AndroidAppSourceError("SwirCalendar must not silently read or mutate the device calendar provider.")
def _validate_weather(logic,activity):
    if any(x not in logic for x in ("validLatitude","validLongitude","forecastUrl","providerUrl","temperatureUnit","windUnit")): raise AndroidAppSourceError("SwirWeather host-tested forecast policy drifted.")
    required=("HttpsURLConnection","JSONObject","WeatherPolicy.forecastUrl","getSharedPreferences","Intent.ACTION_VIEW","MAX_RESPONSE_CHARS")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirWeather must retain bounded HTTPS forecast retrieval, owner-selected coordinates and provider attribution.")
    if any(x in activity for x in ("LocationManager","FusedLocationProviderClient","ACCESS_FINE_LOCATION","ACCESS_COARSE_LOCATION")): raise AndroidAppSourceError("SwirWeather source stage must not collect device location without a reviewed permission flow.")
def _validate_gallery(logic,activity):
    if any(x not in logic for x in ("supportedMime","matches","isVideo","safeEpochSeconds")): raise AndroidAppSourceError("SwirGallery host-tested media policy drifted.")
    if any(x not in activity for x in ("Manifest.permission.READ_MEDIA_IMAGES","Manifest.permission.READ_MEDIA_VIDEO","MediaStore.Files.getContentUri","MediaStore.createDeleteRequest","startIntentSenderForResult","Intent.ACTION_VIEW","Intent.ACTION_SEND","MediaPolicy.matches")): raise AndroidAppSourceError("SwirGallery must retain scoped MediaStore browse/share and owner-confirmed delete flows.")
def _validate_recorder(logic,activity):
    if any(x not in logic for x in ("recordingFileName","isRecordingFile","canExport","canRecord","MAX_EXPORT_BYTES")): raise AndroidAppSourceError("SwirRecorder host-tested recording policy drifted.")
    if any(x not in activity for x in ("Manifest.permission.RECORD_AUDIO","requestPermissions","MediaRecorder.AudioSource.MIC","MediaRecorder.OutputFormat.MPEG_4","MediaRecorder.AudioEncoder.AAC","recorder.pause()","recorder.resume()","getFilesDir()","AudioManager","isMicrophoneMute","Intent.ACTION_CREATE_DOCUMENT","openOutputStream","AlertDialog.Builder","stopRecording(false)")): raise AndroidAppSourceError("SwirRecorder must retain foreground-only recording, microphone state, private storage and explicit export/delete flows.")
def _validate_contacts(logic,activity):
    if any(x not in logic for x in ("validLookupKey","matches","safeExportBase","vcardFileName")): raise AndroidAppSourceError("SwirContacts host-tested contact policy drifted.")
    required=("Manifest.permission.READ_CONTACTS","requestPermissions","ContactsContract.Contacts.CONTENT_URI","ContactsContract.CommonDataKinds.Phone.CONTENT_URI","Intent.ACTION_INSERT","Intent.ACTION_EDIT","Intent.ACTION_OPEN_DOCUMENT","Intent.ACTION_CREATE_DOCUMENT","ContactsContract.Contacts.CONTENT_VCARD_URI","ContactPolicy.vcardFileName")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirContacts must retain scoped provider browse/search plus explicit import/export hand-offs.")
def _validate_backup(logic,activity):
    if any(x not in logic for x in ("MAX_FILES","MAX_ENTRY_BYTES","MAX_TOTAL_BYTES","validEntryName","safeEntryName","backupFileName","sizeAllowed")): raise AndroidAppSourceError("SwirBackup host-tested archive policy drifted.")
    required=("Intent.ACTION_OPEN_DOCUMENT","Intent.EXTRA_ALLOW_MULTIPLE","Intent.ACTION_CREATE_DOCUMENT","ZipOutputStream","ZipInputStream","OpenableColumns.DISPLAY_NAME","Build.FINGERPRINT","copyLimited")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirBackup must retain owner-selected bounded archive creation and safe structural inspection.")
    if any(x in activity for x in ("ZipFile.extract","FileOutputStream","getDataDirectory()","/data/")): raise AndroidAppSourceError("SwirBackup source stage must not restore arbitrary archive entries or read app-private data.")
def _validate_apps(logic,activity):
    if any(x not in logic for x in ("validPackageName","matches","sha256","shortDigest")): raise AndroidAppSourceError("SwirApps host-tested catalog policy drifted.")
    required=("queryIntentActivities","PackageManager.GET_SIGNING_CERTIFICATES","getApkContentsSigners","getLaunchIntentForPackage","Settings.ACTION_APPLICATION_DETAILS_SETTINGS","AppCatalogPolicy.sha256")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirApps must retain local launcher catalog and signing-certificate provenance.")
def _validate_swirroot(logic:str,activity:str,java_bundle:str)->None:
    if any(token not in logic for token in ("State.UNAVAILABLE","exactBuildMatch","verifiedDeviceProfile","ownerConfirmed","rollbackMaterialVerified","journalAvailable","updateStateSafe","expectedNonRootStateKnown","writeBackendEnabled","supportedBuild","evaluateEnable","evaluateUnroot")): raise AndroidAppSourceError("SwirRoot must retain the complete fail-closed enable/unroot gate model.")
    if any(token not in activity for token in ("AlertDialog.Builder","bindService","SwirRootService.class","service.reviewEnable(true)","service.reviewUnroot(true)","service.currentBuildFingerprint()","R.string")): raise AndroidAppSourceError("SwirRoot must retain explicit owner review and localized status UI.")
    if any(token not in java_bundle for token in ("class SwirRootService extends Service","WRITE_BACKEND_ENABLED = false","SUPPORTED_BUILD = false","RootPolicy.State.UNAVAILABLE","auditSnapshot()","reviewEnable","reviewUnroot")): raise AndroidAppSourceError("SwirRoot source stage must retain its non-exported fail-closed status/audit service.")
    if any(token in java_bundle for token in ("RecoverySystem.installPackage","/dev/block/","android.os.SystemProperties","bootctl","setprop","flash ","erase ")): raise AndroidAppSourceError("SwirRoot source stage must not contain a root/device mutation primitive.")

_VALIDATORS={"phone":_validate_phone,"messages":_validate_messages,"camera":_validate_camera,"calculator":_validate_calculator,"settings":_validate_settings,"files":_validate_files,"browser":_validate_browser,"device_care":_validate_device_care,"update":_validate_update,"privacy":_validate_privacy,"clock":_validate_clock,"notes":_validate_notes,"calendar":_validate_calendar,"weather":_validate_weather,"gallery":_validate_gallery,"recorder":_validate_recorder,"contacts":_validate_contacts,"backup":_validate_backup,"apps":_validate_apps}


def validate_android_app_sources(product_root:Path=Path("platform/aosp_product"),registry_path:Path=Path("system_apps/manifest.json"))->AndroidAppSourceSummary:
    registry:SystemAppRegistry=load_registry(registry_path)
    overclaimed=[app.app_id for app in registry.apps if app.status in {"ANDROID_RUNTIME","HARDWARE_VERIFIED"}]
    if overclaimed: raise AndroidAppSourceError(f"Android runtime/hardware states require runtime evidence, not source validation: {overclaimed}")
    source_apps=[app for app in registry.apps if app.status=="ANDROID_SOURCE"]
    if not source_apps: raise AndroidAppSourceError("At least one checked-in Android source app is required.")
    unknown=sorted(app.app_id for app in source_apps if app.app_id not in _SPECS)
    if unknown: raise AndroidAppSourceError(f"ANDROID_SOURCE apps have no reviewed source contract: {unknown}")
    product_mk=_read(product_root/"swirphoneos_cf_x86_64.mk"); staged=_load_stage_sources(product_root)
    localized=0; source_files=0; target=[]; implemented=[]; ids=[]; missing_app=[]
    for app in source_apps:
        spec=_SPECS[app.app_id]; count,staged_count,logic,activity,java_bundle=_validate_common(product_root,product_mk,app,spec,staged)
        if app.app_id=="swirroot": _validate_swirroot(logic,activity,java_bundle)
        else: _VALIDATORS[app.app_id](logic,activity)
        localized+=count; source_files+=staged_count; ids.append(app.app_id); target.extend(app.capabilities); implemented.extend(spec.implemented_capabilities)
        missing_app.extend(f"{app.app_id}:{cap}" for cap in app.capabilities if cap not in spec.implemented_capabilities)
    return AndroidAppSourceSummary(tuple(ids),localized,source_files,tuple(dict.fromkeys(target)),tuple(dict.fromkeys(implemented)),tuple(missing_app))


def public_android_app_source_summary(summary:AndroidAppSourceSummary)->dict[str,object]:
    missing=sorted({item.split(":",1)[1] for item in summary.missing_app_capabilities})
    return {"schema_version":3,"status":"SOURCE_READY_NOT_BUILT","source_ready_apps":list(summary.source_ready_apps),"source_ready_count":len(summary.source_ready_apps),"localized_catalogs":summary.localized_catalogs,"staged_source_files":summary.source_files,"implemented_capabilities":list(summary.implemented_capabilities),"target_capabilities":list(summary.target_capabilities),"remaining_target_capabilities":missing,"remaining_app_capabilities":sorted(summary.missing_app_capabilities),"android_build_verified":False,"runtime_verified":False,"device_write_allowed":False}
