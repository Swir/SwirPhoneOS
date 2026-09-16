"""Offline validation for the SwirPhoneOS Cuttlefish product integration skeleton."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


class ProductContractError(ValueError):
    """Raised when the checked-in AOSP product skeleton drifts from its contract."""


@dataclass(frozen=True)
class ProductContract:
    product_name: str
    base_product: str
    lunch_choice: str
    product_makefile: Path
    android_products: Path


_PRODUCT = re.compile(r"[a-z0-9_]+\Z")


def _read(path: Path) -> str:
    if not path.is_file():
        raise ProductContractError(f"Missing product integration file: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProductContractError("Product integration file is not strict UTF-8.") from exc
    if len(text) > 65536:
        raise ProductContractError("Product integration file is oversized.")
    return text


def validate_product_contract(root: Path) -> ProductContract:
    """Validate syntax-critical identity/inheritance without pretending to run AOSP Kati/Soong."""
    android_products = root / "AndroidProducts.mk"
    product_makefile = root / "swirphoneos_cf_x86_64.mk"
    ap = _read(android_products)
    mk = _read(product_makefile)

    product_name = "swirphoneos_cf_x86_64"
    base_product = "device/google/cuttlefish/vsoc_x86_64_only/phone/aosp_cf.mk"
    lunch_choice = f"{product_name}-aosp_current-userdebug"
    if not _PRODUCT.fullmatch(product_name):
        raise ProductContractError("Invalid product name.")
    required_ap = (
        f"PRODUCT_MAKEFILES := \\\n    $(LOCAL_DIR)/{product_name}.mk",
        f"COMMON_LUNCH_CHOICES := \\\n    {lunch_choice}",
    )
    for snippet in required_ap:
        if snippet not in ap:
            raise ProductContractError("AndroidProducts.mk does not expose the expected product/lunch choice.")

    required_mk = (
        f"$(call inherit-product, {base_product})",
        f"PRODUCT_NAME := {product_name}",
        "PRODUCT_BRAND := Swir",
        "PRODUCT_MANUFACTURER := Swir",
        "PRODUCT_MODEL := SwirPhoneOS Cuttlefish Developer",
    )
    for snippet in required_mk:
        if snippet not in mk:
            raise ProductContractError("Product makefile is missing required SwirPhoneOS identity/inheritance.")
    forbidden = ("PRODUCT_OTA_PUBLIC_KEYS", "PRODUCT_DEFAULT_DEV_CERTIFICATE", "ro.secure=0", "ro.adb.secure=0")
    if any(item in mk for item in forbidden):
        raise ProductContractError("Developer product skeleton weakens signing/security policy.")

    return ProductContract(
        product_name=product_name,
        base_product=base_product,
        lunch_choice=lunch_choice,
        product_makefile=product_makefile,
        android_products=android_products,
    )


def public_product_summary(contract: ProductContract) -> dict[str, object]:
    return {
        "schema_version": 1,
        "product_name": contract.product_name,
        "base_product": contract.base_product,
        "common_lunch_choice": contract.lunch_choice,
        "explicit_android17_lunch": contract.lunch_choice,
        "build_verified": False,
        "boot_verified": False,
        "release_artifact": False,
        "note": "Offline contract only; source sync, Kati/Soong build and Cuttlefish boot are still required.",
    }
