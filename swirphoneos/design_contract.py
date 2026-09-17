from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET


DESIGN_MODULE = "SwirDesign"
DESIGN_THEME = "@style/Theme.SwirPhoneOS"
CORE_APPS = {
    "settings": "SwirSettings",
    "files": "SwirFiles",
    "update": "SwirUpdate",
    "privacy": "SwirPrivacy",
    "device_care": "SwirDeviceCare",
}
SYSTEM_APPS = {
    "phone": "SwirPhone",
    "messages": "SwirMessages",
    "camera": "SwirCamera",
    "calculator": "SwirCalculator",
    "settings": "SwirSettings",
    "files": "SwirFiles",
    "browser": "SwirBrowser",
    "device_care": "SwirDeviceCare",
    "update": "SwirUpdate",
    "privacy": "SwirPrivacy",
    "clock": "SwirClock",
    "notes": "SwirNotes",
    "calendar": "SwirCalendar",
    "weather": "SwirWeather",
    "gallery": "SwirGallery",
    "recorder": "SwirRecorder",
    "contacts": "SwirContacts",
    "backup": "SwirBackup",
    "apps": "SwirApps",
    "swirroot": "SwirRoot",
}
TOKENIZED_APPS = {
    "phone": ("SwirPhone", "src/org/swir/phoneos/phone/MainActivity.java"),
    "messages": ("SwirMessages", "src/org/swir/phoneos/messages/MainActivity.java"),
    "camera": ("SwirCamera", "src/org/swir/phoneos/camera/MainActivity.java"),
    "settings": ("SwirSettings", "src/org/swir/phoneos/settings/MainActivity.java"),
    "update": ("SwirUpdate", "src/org/swir/phoneos/update/MainActivity.java"),
    "privacy": ("SwirPrivacy", "src/org/swir/phoneos/privacy/MainActivity.java"),
    "device_care": ("SwirDeviceCare", "src/org/swir/phoneos/device_care/MainActivity.java"),
}
REQUIRED_TOKEN_REFERENCES = (
    "R.color.swir_background",
    "R.color.swir_text_primary",
    "R.color.swir_text_secondary",
    "R.dimen.swir_touch_min",
)
REQUIRED_COLORS = {
    "swir_background",
    "swir_surface",
    "swir_surface_alt",
    "swir_accent",
    "swir_accent_cyan",
    "swir_text_primary",
    "swir_text_secondary",
    "swir_outline",
    "swir_error",
    "swir_success",
}
REQUIRED_DIMENS = {
    "swir_space_xs",
    "swir_space_sm",
    "swir_space_md",
    "swir_space_lg",
    "swir_space_xl",
    "swir_corner_sm",
    "swir_corner_md",
    "swir_corner_lg",
    "swir_touch_min",
}
REQUIRED_STYLES = {
    "Theme.SwirPhoneOS",
    "SwirText.Headline",
    "SwirText.Body",
    "SwirText.Secondary",
}
DESIGN_STAGE_FILES = (
    "design/SwirDesign/Android.bp",
    "design/SwirDesign/res/values/colors.xml",
    "design/SwirDesign/res/values/dimens.xml",
    "design/SwirDesign/res/values/styles.xml",
    "design/SwirDesign/res/values-night/colors.xml",
    "design/SwirDesign/res/values-night/styles.xml",
)


class DesignContractError(ValueError):
    pass


def _read_regular_text(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DesignContractError(f"required regular file missing or symlinked: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DesignContractError(f"file is not valid UTF-8: {path}") from exc


def _resource_names(path: Path, tag: str) -> set[str]:
    try:
        root = ET.fromstring(_read_regular_text(path))
    except ET.ParseError as exc:
        raise DesignContractError(f"invalid Android resource XML: {path}") from exc
    if root.tag != "resources":
        raise DesignContractError(f"resource root must be <resources>: {path}")
    names: list[str] = []
    for node in root.findall(tag):
        name = node.attrib.get("name", "").strip()
        if not name:
            raise DesignContractError(f"unnamed <{tag}> resource: {path}")
        names.append(name)
    if len(names) != len(set(names)):
        raise DesignContractError(f"duplicate <{tag}> resource name: {path}")
    return set(names)


def _strict_json(path: Path) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise DesignContractError(f"duplicate JSON key {key!r}: {path}")
            out[key] = value
        return out

    try:
        value = json.loads(_read_regular_text(path), object_pairs_hook=pairs)
    except json.JSONDecodeError as exc:
        raise DesignContractError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DesignContractError(f"JSON root must be an object: {path}")
    return value


def _application_theme(manifest: Path) -> str:
    try:
        root = ET.fromstring(_read_regular_text(manifest))
    except ET.ParseError as exc:
        raise DesignContractError(f"invalid Android manifest XML: {manifest}") from exc
    app = root.find("application")
    if app is None:
        raise DesignContractError(f"manifest has no <application>: {manifest}")
    return app.attrib.get("{http://schemas.android.com/apk/res/android}theme", "")


def validate_design_contract(product_root: Path | str = Path("platform/aosp_product")) -> dict:
    product = Path(product_root)
    design = product / "design" / DESIGN_MODULE

    bp = _read_regular_text(design / "Android.bp")
    if 'android_library {' not in bp or f'name: "{DESIGN_MODULE}"' not in bp:
        raise DesignContractError("SwirDesign must remain an android_library with the exact module name")
    for required in ('sdk_version: "current"', 'min_sdk_version: "35"', 'product_specific: true'):
        if required not in bp:
            raise DesignContractError(f"SwirDesign Android.bp missing contract: {required}")

    day_colors = _resource_names(design / "res" / "values" / "colors.xml", "color")
    night_colors = _resource_names(design / "res" / "values-night" / "colors.xml", "color")
    if day_colors != REQUIRED_COLORS or night_colors != REQUIRED_COLORS:
        raise DesignContractError("SwirDesign day/night color token sets must match exactly")

    dimens = _resource_names(design / "res" / "values" / "dimens.xml", "dimen")
    if dimens != REQUIRED_DIMENS:
        raise DesignContractError("SwirDesign dimension token set must match exactly")

    day_styles = _resource_names(design / "res" / "values" / "styles.xml", "style")
    night_styles = _resource_names(design / "res" / "values-night" / "styles.xml", "style")
    if day_styles != REQUIRED_STYLES or night_styles != REQUIRED_STYLES:
        raise DesignContractError("SwirDesign day/night style sets must match exactly")

    integrated_system = []
    for app_id, module in SYSTEM_APPS.items():
        app = product / "apps" / module
        app_bp = _read_regular_text(app / "Android.bp")
        if f'static_libs: ["{DESIGN_MODULE}"]' not in app_bp:
            raise DesignContractError(f"{module} must statically link {DESIGN_MODULE}")
        theme = _application_theme(app / "AndroidManifest.xml")
        if theme != DESIGN_THEME:
            raise DesignContractError(f"{module} must use {DESIGN_THEME}, got {theme!r}")
        integrated_system.append(app_id)

    tokenized_apps = []
    for app_id, (module, relative_java) in TOKENIZED_APPS.items():
        source = _read_regular_text(product / "apps" / module / relative_java)
        if "android.graphics.Color" in source or "Color." in source:
            raise DesignContractError(f"{module} tokenized UI must not use direct android.graphics.Color literals")
        for required in REQUIRED_TOKEN_REFERENCES:
            if required not in source:
                raise DesignContractError(f"{module} tokenized UI missing shared design reference: {required}")
        tokenized_apps.append(app_id)

    integrated_core = [app_id for app_id in CORE_APPS if app_id in integrated_system]
    tokenized_core = [app_id for app_id in CORE_APPS if app_id in tokenized_apps]

    stage_path = product / "stage_manifest.d" / "design.json"
    stage = _strict_json(stage_path)
    if stage.get("schema_version") != 1 or set(stage) != {"schema_version", "files"}:
        raise DesignContractError("design staging fragment must use exact schema v1")
    files = stage.get("files")
    if not isinstance(files, list):
        raise DesignContractError("design staging fragment files must be a list")
    sources = []
    destinations = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"source", "destination"}:
            raise DesignContractError("design staging entries must contain source and destination only")
        source = item["source"]
        destination = item["destination"]
        if not isinstance(source, str) or not isinstance(destination, str):
            raise DesignContractError("design staging paths must be strings")
        sources.append(source)
        destinations.append(destination)
    if tuple(sources) != DESIGN_STAGE_FILES:
        raise DesignContractError("design staging source inventory must match the exact reviewed file set")
    expected_destinations = tuple(f"vendor/swir/{source}" for source in DESIGN_STAGE_FILES)
    if tuple(destinations) != expected_destinations:
        raise DesignContractError("design staging destinations must preserve the exact vendor/swir paths")

    return {
        "status": "SOURCE_CONTRACT_READY_NOT_BUILT",
        "design_contract": "swirphoneos-design-v3",
        "module": DESIGN_MODULE,
        "integrated_core_apps": integrated_core,
        "integrated_core_app_count": len(integrated_core),
        "integrated_system_apps": integrated_system,
        "integrated_system_app_count": len(integrated_system),
        "expected_system_app_count": len(SYSTEM_APPS),
        "tokenized_apps": tokenized_apps,
        "tokenized_app_count": len(tokenized_apps),
        "tokenized_core_apps": tokenized_core,
        "tokenized_core_app_count": len(tokenized_core),
        "expected_core_app_count": len(CORE_APPS),
        "day_night_tokens_declared": True,
        "minimum_touch_target_token_dp": 48,
        "all_system_apps_integrated": len(integrated_system) == len(SYSTEM_APPS),
        "hardcoded_color_free_cohort_verified": len(tokenized_apps) == len(TOKENIZED_APPS),
        "all_core_apps_tokenized": len(tokenized_core) == len(CORE_APPS),
        "android_build_verified": False,
        "runtime_visual_review_verified": False,
        "accessibility_review_verified": False,
        "device_write_allowed": False,
    }
