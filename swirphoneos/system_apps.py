"""Validated first-party application registry for SwirPhoneOS."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

APP_ID = re.compile(r"[a-z][a-z0-9_]{1,31}\Z")
PACKAGE = re.compile(r"org\.swir\.phoneos\.[a-z][a-z0-9_.]{1,63}\Z")
ALLOWED_PHASES = {"emulator_core", "reference_hardware", "beta_integration"}
ALLOWED_STATUS = {"PLANNED", "HOST_CONTRACT", "ANDROID_SOURCE", "ANDROID_RUNTIME", "HARDWARE_VERIFIED"}
EXPECTED_DESIGN_CONTRACT = "swirphoneos-design-v6"
REQUIRED_APP_IDS = frozenset({"phone","contacts","messages","camera","gallery","files","settings","browser","clock","calculator","notes","recorder","calendar","weather","update","backup","privacy","device_care","apps","swirroot"})
REQUIRED_KEYS = {"id","package","display_name","phase","status","hardware_dependent","critical_for_beta","capabilities"}


class SystemAppRegistryError(ValueError):
    """Raised when the system-app registry overclaims or is malformed."""


@dataclass(frozen=True)
class SystemApp:
    app_id: str
    package: str
    display_name: str
    phase: str
    status: str
    hardware_dependent: bool
    critical_for_beta: bool
    capabilities: tuple[str, ...]

    @property
    def source_ready(self) -> bool:
        return self.status in {"ANDROID_SOURCE", "ANDROID_RUNTIME", "HARDWARE_VERIFIED"}

    @property
    def runtime_implemented(self) -> bool:
        return self.status in {"ANDROID_RUNTIME", "HARDWARE_VERIFIED"}

    @property
    def hardware_verified(self) -> bool:
        return self.status == "HARDWARE_VERIFIED"


@dataclass(frozen=True)
class SystemAppRegistry:
    namespace: str
    design_contract: str
    source_language: str
    apps: tuple[SystemApp, ...]

    @property
    def app_ids(self) -> frozenset[str]:
        return frozenset(app.app_id for app in self.apps)


def _load_json(path: Path) -> object:
    if not path.is_file():
        raise SystemAppRegistryError("System-app manifest does not exist.")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SystemAppRegistryError("System-app manifest cannot be read.") from exc
    if len(text) > 262_144:
        raise SystemAppRegistryError("System-app manifest is oversized.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemAppRegistryError("System-app manifest is invalid JSON.") from exc


def _safe_text(value: object, field: str, limit: int = 160) -> str:
    if not isinstance(value, str):
        raise SystemAppRegistryError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit:
        raise SystemAppRegistryError(f"{field} is invalid.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise SystemAppRegistryError(f"{field} contains control characters.")
    return value


def validate_registry(data: object) -> SystemAppRegistry:
    if not isinstance(data, dict) or set(data) != {"schema_version","namespace","design_contract","source_language","apps"}:
        raise SystemAppRegistryError("System-app manifest must match schema v1 exactly.")
    if data["schema_version"] != 1:
        raise SystemAppRegistryError("Unsupported system-app manifest schema.")
    namespace = _safe_text(data["namespace"], "namespace", 80)
    if namespace != "org.swir.phoneos": raise SystemAppRegistryError("Unexpected application namespace.")
    design_contract = _safe_text(data["design_contract"], "design_contract", 80)
    if design_contract != EXPECTED_DESIGN_CONTRACT:
        raise SystemAppRegistryError(
            f"System-app manifest design contract must be {EXPECTED_DESIGN_CONTRACT}."
        )
    source_language = _safe_text(data["source_language"], "source_language", 16)
    if source_language != "en": raise SystemAppRegistryError("English must remain the canonical fallback language.")
    raw_apps = data["apps"]
    if not isinstance(raw_apps, list) or not raw_apps: raise SystemAppRegistryError("System-app manifest must contain apps.")
    apps: list[SystemApp] = []
    ids: set[str] = set()
    packages: set[str] = set()
    for raw in raw_apps:
        if not isinstance(raw, dict) or set(raw) != REQUIRED_KEYS: raise SystemAppRegistryError("Every system app must match schema v1 exactly.")
        app_id = _safe_text(raw["id"], "id", 32)
        package = _safe_text(raw["package"], "package", 96)
        display_name = _safe_text(raw["display_name"], "display_name", 80)
        phase = _safe_text(raw["phase"], "phase", 32)
        status = _safe_text(raw["status"], "status", 32)
        if not APP_ID.fullmatch(app_id): raise SystemAppRegistryError("System app id is invalid.")
        if not PACKAGE.fullmatch(package): raise SystemAppRegistryError(f"Package for {app_id} is outside the SwirPhoneOS namespace.")
        if app_id in ids or package in packages: raise SystemAppRegistryError("System app ids and packages must be unique.")
        if phase not in ALLOWED_PHASES or status not in ALLOWED_STATUS: raise SystemAppRegistryError(f"Unknown phase/status for {app_id}.")
        hardware_dependent = raw["hardware_dependent"]
        critical_for_beta = raw["critical_for_beta"]
        if type(hardware_dependent) is not bool or type(critical_for_beta) is not bool: raise SystemAppRegistryError("System app flags must be booleans.")
        capabilities = raw["capabilities"]
        if not isinstance(capabilities, list) or not capabilities or len(capabilities) > 32: raise SystemAppRegistryError(f"{app_id} must define bounded capabilities.")
        clean: list[str] = []
        for capability in capabilities:
            capability = _safe_text(capability, "capability", 96)
            if capability in clean: raise SystemAppRegistryError(f"{app_id} contains duplicate capabilities.")
            clean.append(capability)
        if status == "HARDWARE_VERIFIED" and not hardware_dependent:
            raise SystemAppRegistryError(f"{app_id} cannot claim HARDWARE_VERIFIED without a hardware-dependent contract.")
        ids.add(app_id); packages.add(package)
        apps.append(SystemApp(app_id, package, display_name, phase, status, hardware_dependent, critical_for_beta, tuple(clean)))
    if ids != REQUIRED_APP_IDS:
        raise SystemAppRegistryError(f"Essential system-app set mismatch. Missing={sorted(REQUIRED_APP_IDS-ids)}, extra={sorted(ids-REQUIRED_APP_IDS)}.")
    return SystemAppRegistry(namespace, design_contract, source_language, tuple(apps))


def load_registry(path: Path) -> SystemAppRegistry:
    return validate_registry(_load_json(path))


def public_registry_summary(registry: SystemAppRegistry) -> dict[str, object]:
    source_ready = sum(app.source_ready for app in registry.apps)
    runtime = sum(app.runtime_implemented for app in registry.apps)
    hardware_verified = sum(app.hardware_verified for app in registry.apps)
    beta_critical = [app for app in registry.apps if app.critical_for_beta]
    beta_runtime = sum(app.runtime_implemented for app in beta_critical)
    return {
        "schema_version": 1, "namespace": registry.namespace, "design_contract": registry.design_contract,
        "source_language": registry.source_language, "app_count": len(registry.apps), "source_ready": source_ready,
        "runtime_implemented": runtime, "hardware_verified": hardware_verified, "beta_critical_count": len(beta_critical),
        "beta_critical_runtime_implemented": beta_runtime,
        "apps": [{"id": app.app_id,"package": app.package,"display_name": app.display_name,"phase": app.phase,"status": app.status,"hardware_dependent": app.hardware_dependent,"critical_for_beta": app.critical_for_beta} for app in registry.apps],
    }
