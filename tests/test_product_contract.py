from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.product_contract import ProductContractError, public_product_summary, validate_product_contract


FIRST_BETA_PRODUCT_PACKAGES = (
    "SwirLauncher",
    "SwirSettings",
    "SwirFiles",
    "SwirDeviceCare",
    "SwirUpdate",
    "SwirPrivacy",
    "SwirRoot",
)


def _explicit_product_packages(path: Path) -> tuple[str, ...]:
    """Read the one explicit PRODUCT_PACKAGES += block used by Swir products."""
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "PRODUCT_PACKAGES += \\")
    except StopIteration as exc:
        raise AssertionError(f"{path.name} has no explicit PRODUCT_PACKAGES block") from exc

    packages: list[str] = []
    for line in lines[start + 1:]:
        value = line.strip()
        if not value:
            break
        continued = value.endswith("\\")
        if continued:
            value = value[:-1].strip()
        packages.append(value)
        if not continued:
            break
    return tuple(packages)


class ProductContractTests(unittest.TestCase):
    def test_checked_in_contract(self):
        contract = validate_product_contract(Path("platform/aosp_product"))
        summary = public_product_summary(contract)
        self.assertEqual(summary["product_name"], "swirphoneos_cf_x86_64")
        self.assertFalse(summary["build_verified"])
        self.assertFalse(summary["boot_verified"])

    def test_first_beta_products_package_only_frozen_scope(self):
        root = Path("platform/aosp_product")
        for name in ("swirphoneos_cf_x86_64.mk", "swirphoneos_gsi_arm64.mk"):
            with self.subTest(product=name):
                self.assertEqual(
                    _explicit_product_packages(root / name),
                    FIRST_BETA_PRODUCT_PACKAGES,
                    "First-Beta product scope drifted; post-Beta apps must stay out of the image.",
                )

    def test_security_weakening_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AndroidProducts.mk").write_text(
                "PRODUCT_MAKEFILES := \\\n    $(LOCAL_DIR)/swirphoneos_cf_x86_64.mk\n\n"
                "COMMON_LUNCH_CHOICES := \\\n    swirphoneos_cf_x86_64-aosp_current-userdebug\n",
                encoding="utf-8",
            )
            (root / "swirphoneos_cf_x86_64.mk").write_text(
                "$(call inherit-product, device/google/cuttlefish/vsoc_x86_64_only/phone/aosp_cf.mk)\n"
                "PRODUCT_NAME := swirphoneos_cf_x86_64\nPRODUCT_BRAND := Swir\n"
                "PRODUCT_MANUFACTURER := Swir\nPRODUCT_MODEL := SwirPhoneOS Cuttlefish Developer\n"
                "ro.secure=0\n",
                encoding="utf-8",
            )
            with self.assertRaises(ProductContractError):
                validate_product_contract(root)


if __name__ == "__main__":
    unittest.main()
