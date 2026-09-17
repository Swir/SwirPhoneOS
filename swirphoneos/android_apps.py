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
    "phone": _AppSpec("phone","SwirPhone","SwirPhone","org.swir.phoneos.phone","src/org/swir/phoneos/phone/DialerPolicy.java","src/org/swir/phoneos/phone/MainActivity.java","hosttest/DialerPolicyHostTest.java","res/drawable/ic_phone.xml",("dialer",)),
    "calculator": _AppSpec("calculator","SwirCalculator","SwirCalculator","org.swir.phoneos.calculator","src/org/swir/phoneos/calculator/CalculatorEngine.java","src/org/swir/phoneos/calculator/MainActivity.java","hosttest/CalculatorEngineHostTest.java","res/drawable/ic_calculator.xml",("basic_math",)),
    "settings": _AppSpec("settings","SwirSettings","SwirSettings","org.swir.phoneos.settings","src/org/swir/phoneos/settings/SettingsCatalog.java","src/org/swir/phoneos/settings/MainActivity.java","hosttest/SettingsCatalogHostTest.java","res/drawable/ic_settings.xml",("system_settings","search","device_status")),
    "files": _AppSpec("files","SwirFiles","SwirFiles","org.swir.phoneos.files","src/org/swir/phoneos/files/FilePolicy.java","src/org/swir/phoneos/files/MainActivity.java","hosttest/FilePolicyHostTest.java","res/drawable/ic_files.xml",("browse","search","copy_move_rename","share","safe_delete")),
    "device_care": _AppSpec("device_care","SwirDeviceCare","SwirDeviceCare","org.swir.phoneos.device_care","src/org/swir/phoneos/device_care/HealthModel.java","src/org/swir/phoneos/device_care/MainActivity.java","hosttest/HealthModelHostTest.java","res/drawable/ic_device_care.xml",("storage_status","battery_status","thermal_status","hardware_diagnostics")),
    "update": _AppSpec("update","SwirUpdate","SwirUpdate","org.swir.phoneos.update","src/org/swir/phoneos/update/UpdatePolicy.java","src/org/swir/phoneos/update/MainActivity.java","hosttest/UpdatePolicyHostTest.java","res/drawable/ic_update.xml",("channel_status","signed_metadata")),
    "privacy": _AppSpec("privacy","SwirPrivacy","SwirPrivacy","org.swir.phoneos.privacy","src/org/swir/phoneos/privacy/PrivacyCatalog.java","src/org/swir/phoneos/privacy/MainActivity.java","hosttest/PrivacyCatalogHostTest.java","res/drawable/ic_privacy.xml",("permission_review",)),
    "clock": _AppSpec("clock","SwirClock","SwirClock","org.swir.phoneos.clock","src/org/swir/phoneos/clock/ClockCore.java","src/org/swir/phoneos/clock/MainActivity.java","hosttest/ClockCoreHostTest.java","res/drawable/ic_clock.xml",("alarms","timers","stopwatch","world_clock")),
    "notes": _AppSpec("notes","SwirNotes","SwirNotes","org.swir.phoneos.notes","src/org/swir/phoneos/notes/NotePolicy.java","src/org/swir/phoneos/notes/MainActivity.java","hosttest/NotePolicyHostTest.java","res/drawable/ic_notes.xml",("offline_notes","export","share")),
    "calendar": _AppSpec("calendar","SwirCalendar","SwirCalendar","org.swir.phoneos.calendar","src/org/swir/phoneos/calendar/EventPolicy.java","src/org/swir/phoneos/calendar/MainActivity.java","hosttest/EventPolicyHostTest.java","res/drawable/ic_calendar.xml",("local_calendar",)),
    "gallery": _AppSpec("gallery","SwirGallery","SwirGallery","org.swir.phoneos.gallery","src/org/swir/phoneos/gallery/MediaPolicy.java","src/org/swir/phoneos/gallery/MainActivity.java","hosttest/MediaPolicyHostTest.java","res/drawable/ic_gallery.xml",("local_media","share","safe_delete"),("android.permission.READ_MEDIA_IMAGES","android.permission.READ_MEDIA_VIDEO")),
    "recorder": _AppSpec("recorder","SwirRecorder","SwirRecorder","org.swir.phoneos.recorder","src/org/swir/phoneos/recorder/RecorderPolicy.java","src/org/swir/phoneos/recorder/MainActivity.java","hosttest/RecorderPolicyHostTest.java","res/drawable/ic_recorder.xml",("audio_recording","microphone_state","file_export"),("android.permission.RECORD_AUDIO",)),
    "contacts": _AppSpec("contacts","SwirContacts","SwirContacts","org.swir.phoneos.contacts","src/org/swir/phoneos/contacts/ContactPolicy.java","src/org/swir/phoneos/contacts/MainActivity.java","hosttest/ContactPolicyHostTest.java","res/drawable/ic_contacts.xml",("local_contacts","import_export","provider_bridge"),("android.permission.READ_CONTACTS",)),
    "apps": _AppSpec("apps","SwirApps","SwirApps","org.swir.phoneos.apps","src/org/swir/phoneos/apps/AppCatalogPolicy.java","src/org/swir/phoneos/apps/MainActivity.java","hosttest/AppCatalogPolicyHostTest.java","res/drawable/ic_apps.xml",("package_catalog","signature_provenance")),
    "swirroot": _AppSpec("swirroot","SwirRoot","SwirRoot","org.swir.phoneos.swirroot","src/org/swir/phoneos/swirroot/RootPolicy.java","src/org/swir/phoneos/swirroot/MainActivity.java","hosttest/RootPolicyHostTest.java","res/drawable/ic_swirroot.xml",("root_state","authorization_audit")),
}
_SETTINGS_ACTIONS = frozenset({"android.settings.WIFI_SETTINGS","android.settings.BLUETOOTH_SETTINGS","android.settings.DISPLAY_SETTINGS","android.settings.SOUND_SETTINGS","android.settings.SECURITY_SETTINGS","android.settings.PRIVACY_SETTINGS","android.settings.ACCESSIBILITY_SETTINGS","android.settings.LOCALE_SETTINGS","android.settings.INTERNAL_STORAGE_SETTINGS","android.settings.APPLICATION_SETTINGS"})
_PRIVACY_ACTIONS = frozenset({"android.settings.PRIVACY_SETTINGS","android.settings.MANAGE_PERMISSIONS","android.settings.LOCATION_SOURCE_SETTINGS","android.settings.APPLICATION_SETTINGS","android.settings.MANAGE_SPECIAL_APP_ACCESSES"})


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
    forbidden=("Runtime.getRuntime","ProcessBuilder","android.permission.INTERNET",'"su"',"DexClassLoader","System.loadLibrary","MANAGE_EXTERNAL_STORAGE","READ_EXTERNAL_STORAGE","WRITE_EXTERNAL_STORAGE")
    if any(token in java_bundle or token in manifest_text for token in forbidden): raise AndroidAppSourceError(f"{spec.module} source contains a forbidden execution/network/storage primitive.")
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
    required=("Intent.ACTION_DIAL",'Uri.fromParts("tel"',"resolveActivity(getPackageManager())","startActivity(intent)","DialerPolicy.normalize","R.array.dial_keys")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirPhone must retain explicit user-visible system dialer handoff and the reviewed keypad policy.")
    if any(x in activity for x in ("Intent.ACTION_CALL","TelecomManager.placeCall","CallLog.Calls","Manifest.permission.CALL_PHONE")): raise AndroidAppSourceError("SwirPhone source stage must not place calls directly or claim call-log/in-call support.")
def _validate_calculator(logic,activity):
    if "java.math.BigDecimal" not in logic or "equalsResult" not in logic: raise AndroidAppSourceError("SwirCalculator must retain its host-tested decimal engine.")
    if "DecimalFormatSymbols" not in activity: raise AndroidAppSourceError("SwirCalculator must preserve locale-aware decimal display.")
def _validate_settings(logic,activity):
    if frozenset(re.findall(r'"(android\.settings\.[A-Z_]+)"',logic))!=_SETTINGS_ACTIONS: raise AndroidAppSourceError("SwirSettings routes must match the reviewed public-settings allowlist exactly.")
    if any(x not in activity for x in ("Build.MODEL","Build.VERSION.RELEASE","Build.VERSION.SDK_INT","startActivity(new Intent(entry.action()))")): raise AndroidAppSourceError("SwirSettings must expose real device state and reviewed routes.")
def _validate_files(logic,activity):
    required=("Intent.ACTION_OPEN_DOCUMENT_TREE","takePersistableUriPermission","DocumentsContract.buildChildDocumentsUriUsingTree","DocumentsContract.createDocument","DocumentsContract.renameDocument","DocumentsContract.copyDocument","DocumentsContract.moveDocument","DocumentsContract.deleteDocument","Intent.FLAG_GRANT_READ_URI_PERMISSION","Intent.FLAG_GRANT_WRITE_URI_PERMISSION")
    if any(x not in activity for x in required) or "validName" not in logic or "Character.isISOControl" not in logic: raise AndroidAppSourceError("SwirFiles must retain its reviewed user-granted SAF workflow and file policy.")
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
    if any(x not in logic for x in ("normalizeEnd","matches","escapeIcs","toIcs","BEGIN:VCALENDAR")): raise AndroidAppSourceError("SwirCalendar event/ICS policy drifted.")
    if any(x not in activity for x in ("SQLiteOpenHelper","DatePickerDialog","TimePickerDialog","Intent.ACTION_CREATE_DOCUMENT","Intent.ACTION_SEND","EventPolicy.toIcs")) or "CalendarContract" in activity: raise AndroidAppSourceError("SwirCalendar must remain local-first until provider integration is reviewed.")
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
def _validate_apps(logic,activity):
    if any(x not in logic for x in ("validPackageName","matches","sha256","shortDigest")): raise AndroidAppSourceError("SwirApps host-tested catalog policy drifted.")
    required=("queryIntentActivities","PackageManager.GET_SIGNING_CERTIFICATES","getApkContentsSigners","getLaunchIntentForPackage","Settings.ACTION_APPLICATION_DETAILS_SETTINGS","AppCatalogPolicy.sha256")
    if any(x not in activity for x in required): raise AndroidAppSourceError("SwirApps must retain local launcher catalog and signing-certificate provenance.")
def _validate_swirroot(logic:str,activity:str,java_bundle:str)->None:
    if any(token not in logic for token in ("State.UNAVAILABLE","exactBuildMatch","verifiedDeviceProfile","ownerConfirmed","rollbackMaterialVerified","journalAvailable","updateStateSafe","expectedNonRootStateKnown","writeBackendEnabled","supportedBuild","evaluateEnable","evaluateUnroot")): raise AndroidAppSourceError("SwirRoot must retain the complete fail-closed enable/unroot gate model.")
    if any(token not in activity for token in ("AlertDialog.Builder","bindService","SwirRootService.class","service.reviewEnable(true)","service.reviewUnroot(true)","service.currentBuildFingerprint()","R.string")): raise AndroidAppSourceError("SwirRoot must retain explicit owner review and localized status UI.")
    if any(token not in java_bundle for token in ("class SwirRootService extends Service","WRITE_BACKEND_ENABLED = false","SUPPORTED_BUILD = false","RootPolicy.State.UNAVAILABLE","auditSnapshot()","reviewEnable","reviewUnroot")): raise AndroidAppSourceError("SwirRoot source stage must retain its non-exported fail-closed status/audit service.")
    if any(token in java_bundle for token in ("RecoverySystem.installPackage","/dev/block/","android.os.SystemProperties","bootctl","setprop","flash ","erase ")): raise AndroidAppSourceError("SwirRoot source stage must not contain a root/device mutation primitive.")

_VALIDATORS={"phone":_validate_phone,"calculator":_validate_calculator,"settings":_validate_settings,"files":_validate_files,"device_care":_validate_device_care,"update":_validate_update,"privacy":_validate_privacy,"clock":_validate_clock,"notes":_validate_notes,"calendar":_validate_calendar,"gallery":_validate_gallery,"recorder":_validate_recorder,"contacts":_validate_contacts,"apps":_validate_apps}


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
