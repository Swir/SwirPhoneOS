"""Offline, fail-closed validation for the SwirPhoneOS ARM64 GSI product source."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .stage_manifest import StageManifestError, load_stage_files


class GsiContractError(ValueError):
    """Raised when the checked-in ARM64 GSI product drifts from its reviewed contract."""


@dataclass(frozen=True)
class GsiContract:
    product_name: str
    device: str
    architecture: str
    base_product: str
    gsi_release: str
    lunch_choice: str
    product_makefile: Path
    android_products: Path
    package_modules: tuple[str, ...]


_PRODUCT = re.compile(r"[a-z0-9_]+\Z")
_EXPECTED_MODULES = (
    "SwirPhone",
    "SwirMessages",
    "SwirCamera",
    "SwirCalculator",
    "SwirSettings",
    "SwirFiles",
    "SwirBrowser",
    "SwirDeviceCare",
    "SwirUpdate",
    "SwirPrivacy",
    "SwirClock",
    "SwirNotes",
    "SwirCalendar",
    "SwirWeather",
    "SwirGallery",
    "SwirRecorder",
    "SwirContacts",
    "SwirBackup",
    "SwirApps",
    "SwirRoot",
)
_FORBIDDEN = (
    "PRODUCT_OTA_PUBLIC_KEYS",
    "PRODUCT_DEFAULT_DEV_CERTIFICATE",
    "ro.secure=0",
    "ro.adb.secure=0",
    "ro.debuggable=1",
    "ro.boot.verifiedbootstate=orange",
    "BOARD_AVB_ENABLE := false",
    "PRODUCT_SUPPORTS_VERITY := false",
)


def _read(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise GsiContractError(f"Missing or unsafe GSI product source: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GsiContractError("GSI product source must be readable strict UTF-8.") from exc
    if not text or len(text) > 131_072:
        raise GsiContractError("GSI product source has an invalid size.")
    return text


def validate_gsi_contract(root: Path) -> GsiContract:
    """Validate source identity/staging without claiming a build or Treble compatibility."""
    android_products = root / "AndroidProducts.mk"
    product_makefile = root / "swirphoneos_gsi_arm64.mk"
    ap = _read(android_products)
    mk = _read(product_makefile)

    product_name = "swirphoneos_gsi_arm64"
    device = "generic_arm64"
    architecture = "arm64"
    base_product = "$(SRC_TARGET_DIR)/product/aosp_arm64.mk"
    gsi_release = "$(SRC_TARGET_DIR)/product/gsi_release.mk"
    lunch_choice = f"{product_name}-aosp_current-userdebug"
    if not _PRODUCT.fullmatch(product_name):
        raise GsiContractError("Invalid GSI product name.")

    if f"$(LOCAL_DIR)/{product_name}.mk" not in ap or lunch_choice not in ap:
        raise GsiContractError("AndroidProducts.mk does not expose the reviewed ARM64 GSI product/lunch choice.")

    required_mk = (
        f"$(call inherit-product, {base_product})",
        f"$(call inherit-product, {gsi_release})",
        f"PRODUCT_NAME := {product_name}",
        f"PRODUCT_DEVICE := {device}",
        "PRODUCT_BRAND := Swir",
        "PRODUCT_MANUFACTURER := Swir",
        "PRODUCT_MODEL := SwirPhoneOS ARM64 GSI Developer",
        "PRODUCT_PACKAGES +=",
    )
    if any(snippet not in mk for snippet in required_mk):
        raise GsiContractError("ARM64 GSI product makefile is missing required identity/inheritance/package wiring.")
    if any(item in mk for item in _FORBIDDEN):
        raise GsiContractError("ARM64 GSI product source weakens signing, verified boot or platform security policy.")

    missing_modules = [module for module in _EXPECTED_MODULES if re.search(rf"(?m)^\s*{re.escape(module)}(?:\s*\\)?\s*$", mk) is None]
    if missing_modules:
        raise GsiContractError("ARM64 GSI product is missing one or more essential SwirPhoneOS app modules.")

    try:
        staged = load_stage_files(root)
    except StageManifestError as exc:
        raise GsiContractError(str(exc)) from exc
    expected_source = "swirphoneos_gsi_arm64.mk"
    expected_destination = "vendor/swir/products/swirphoneos_gsi_arm64.mk"
    matches = [
        item for item in staged
        if item.source.as_posix() == expected_source
        and item.destination.as_posix() == expected_destination
    ]
    if len(matches) != 1:
        raise GsiContractError("ARM64 GSI product makefile is not exactly included in bounded AOSP staging.")

    return GsiContract(
        product_name=product_name,
        device=device,
        architecture=architecture,
        base_product=base_product,
        gsi_release=gsi_release,
        lunch_choice=lunch_choice,
        product_makefile=product_makefile,
        android_products=android_products,
        package_modules=_EXPECTED_MODULES,
    )


def public_gsi_contract_summary(contract: GsiContract) -> dict[str, object]:
    return {
        "schema_version": 1,
        "product_name": contract.product_name,
        "device": contract.device,
        "architecture": contract.architecture,
        "base_product": contract.base_product,
        "gsi_release": contract.gsi_release,
        "common_lunch_choice": contract.lunch_choice,
        "source_ready_package_count": len(contract.package_modules),
        "expected_artifact": "out/target/product/generic_arm64/system.img",
        "build_verified": False,
        "treble_vts_verified": False,
        "physical_device_compatibility_verified": False,
        "install_verified": False,
        "device_write_allowed": False,
        "release_artifact": False,
        "note": (
            "Source contract only. A real pinned AOSP systemimage build, Treble/VTS review, "
            "device-specific compatibility and safe install/rollback evidence are still required."
        ),
    }
