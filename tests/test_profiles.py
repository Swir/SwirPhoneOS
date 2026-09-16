from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.profiles import (
    ProfileError,
    discover_profiles,
    load_profile,
    public_profile_summary,
    validate_profile,
)


def valid_profile() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "oneplus/avicii",
        "display_name": "OnePlus Nord AC2003",
        "codename": "avicii",
        "model_allowlist": ["AC2003"],
        "status": "PLANNED_NOT_SUPPORTED",
        "flash_enabled": False,
        "firmware_baseline": None,
        "verified_partition_map": None,
        "validated_builds": [],
        "flash_operations": [],
        "recovery_evidence": [],
        "notes": "Metadata only.",
        "sources": ["https://example.invalid/device"],
    }


class ProfileValidationTests(unittest.TestCase):
    def test_valid_metadata_profile(self) -> None:
        profile = validate_profile(valid_profile())
        self.assertEqual(profile.profile_id, "oneplus/avicii")
        self.assertEqual(profile.codename, "avicii")
        self.assertFalse(profile.flash_allowed)

    def test_schema_v1_cannot_enable_flashing(self) -> None:
        data = valid_profile()
        data["flash_enabled"] = True
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_schema_v1_cannot_carry_flash_operations(self) -> None:
        data = valid_profile()
        data["flash_operations"] = ["fastboot flash boot boot.img"]
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_rejects_unknown_fields(self) -> None:
        data = valid_profile()
        data["surprise"] = "value"
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_rejects_unsafe_profile_id(self) -> None:
        data = valid_profile()
        data["id"] = "../outside"
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_rejects_duplicate_models(self) -> None:
        data = valid_profile()
        data["model_allowlist"] = ["AC2003", "AC2003"]
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_rejects_non_https_source(self) -> None:
        data = valid_profile()
        data["sources"] = ["http://example.invalid/device"]
        with self.assertRaises(ProfileError):
            validate_profile(data)

    def test_public_summary_remains_non_executable(self) -> None:
        summary = public_profile_summary(validate_profile(valid_profile()))
        self.assertFalse(summary["flash_allowed"])
        self.assertNotIn("flash_operations", summary)


class ProfileRegistryTests(unittest.TestCase):
    def test_repository_avicii_profile_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[1]
        profile = load_profile(root / "device_packs" / "oneplus" / "avicii" / "profile.json")
        self.assertEqual(profile.profile_id, "oneplus/avicii")
        self.assertEqual(profile.status, "PLANNED_NOT_SUPPORTED")
        self.assertFalse(profile.flash_allowed)

    def test_discover_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "vendor" / "device"
            target.mkdir(parents=True)
            data = valid_profile()
            data["id"] = "vendor/device"
            data["display_name"] = "Test Device"
            data["codename"] = "device"
            data["model_allowlist"] = ["MODEL1"]
            (target / "profile.json").write_text(json.dumps(data), encoding="utf-8")
            profiles = discover_profiles(root)
            self.assertEqual([profile.profile_id for profile in profiles], ["vendor/device"])

    def test_duplicate_profile_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in ("a", "b"):
                target = root / index
                target.mkdir(parents=True)
                (target / "profile.json").write_text(json.dumps(valid_profile()), encoding="utf-8")
            with self.assertRaises(ProfileError):
                discover_profiles(root)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ProfileError):
                load_profile(path)


if __name__ == "__main__":
    unittest.main()
