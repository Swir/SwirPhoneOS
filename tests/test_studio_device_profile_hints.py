"""Profile-hint tests for SwirPhoneStudio's read-only inventory."""
from __future__ import annotations

from unittest import TestCase

from swirphoneos.profiles import DeviceProfile
from swirphoneos.studio_device_inventory import (
    DeviceInventoryEvidence,
    DeviceObservation,
    DeviceProfileHint,
    assess_inventory_profiles,
)
from swirphoneos.studio_desktop import render_device_inventory


def _profile(
    profile_id: str = "oneplus/avicii",
    display_name: str = "OnePlus Nord AC2003",
    codename: str = "avicii",
    model: str = "AC2003",
) -> DeviceProfile:
    return DeviceProfile(
        profile_id=profile_id,
        display_name=display_name,
        codename=codename,
        model_allowlist=(model,),
        status="PLANNED_NOT_SUPPORTED",
        firmware_baseline=None,
        sources=("https://example.invalid/profile",),
    )


def _evidence(observation: DeviceObservation) -> DeviceInventoryEvidence:
    return DeviceInventoryEvidence(
        observations=(observation,),
        adb_attempted=observation.transport == "adb",
        fastboot_attempted=observation.transport == "fastboot",
    )


class InventoryProfileHintTests(TestCase):
    def test_unique_adb_metadata_match_stays_non_authoritative(self) -> None:
        evidence = _evidence(
            DeviceObservation(
                "adb",
                "a" * 64,
                "device",
                product="avicii",
                model="AC2003",
                device="avicii",
            )
        )

        hints = assess_inventory_profiles(evidence, (_profile(),))

        self.assertEqual(len(hints), 1)
        hint = hints[0]
        self.assertEqual(hint.result, "PROFILE_HINT_ONLY")
        self.assertEqual(hint.candidate_profile_id, "oneplus/avicii")
        self.assertEqual(hint.profile_status, "PLANNED_NOT_SUPPORTED")
        report = hint.to_dict()
        self.assertIs(report["identity_verified"], False)
        self.assertIs(report["physical_verification"], False)
        self.assertEqual(report["swirphoneos_support"], "NOT_VALIDATED")
        self.assertIs(report["support_claim"], False)
        self.assertIs(report["flash_allowed"], False)

    def test_model_only_collision_is_ambiguous_and_selects_nothing(self) -> None:
        evidence = _evidence(
            DeviceObservation("adb", "b" * 64, "device", model="AC2003")
        )
        profiles = (
            _profile(),
            _profile(
                profile_id="example/other",
                display_name="Other device",
                codename="other",
                model="AC2003",
            ),
        )

        hint = assess_inventory_profiles(evidence, profiles)[0]

        self.assertEqual(hint.result, "AMBIGUOUS_PROFILE_HINT")
        self.assertIsNone(hint.candidate_profile_id)
        self.assertIsNone(hint.candidate_display_name)
        self.assertIsNone(hint.profile_status)
        self.assertEqual(hint.evidence, ())

    def test_fastboot_presence_without_product_metadata_cannot_select_profile(self) -> None:
        evidence = _evidence(DeviceObservation("fastboot", "c" * 64, "fastboot"))

        hint = assess_inventory_profiles(evidence, (_profile(),))[0]

        self.assertEqual(hint.result, "NO_PROFILE_HINT")
        self.assertIsNone(hint.candidate_profile_id)

    def test_non_ascii_untrusted_metadata_is_not_used_for_profile_matching(self) -> None:
        evidence = _evidence(
            DeviceObservation(
                "adb",
                "d" * 64,
                "device",
                model="AC2003\u202e",
                device="avicii\u202e",
            )
        )

        hint = assess_inventory_profiles(evidence, (_profile(),))[0]

        self.assertEqual(hint.result, "NO_PROFILE_HINT")
        self.assertIsNone(hint.candidate_profile_id)


class _App:
    def tr(self, key: str, **values: object) -> str:
        if key == "inventory_title":
            return "Inventory"
        if key == "inventory_none":
            return "None"
        if key == "none":
            return "none"
        if key == "inventory_item":
            return "ITEM:{transport}:{state}:{identifier}:{model}".format(**values)
        if key == "inventory_profile_hint":
            return "HINT:{name}:{profile}:{status}".format(**values)
        if key == "inventory_profile_ambiguous":
            return "AMBIGUOUS"
        return key


class InventoryProfileHintRenderingTests(TestCase):
    def test_unique_profile_hint_is_visibly_labeled_as_hint(self) -> None:
        evidence = _evidence(
            DeviceObservation("adb", "e" * 64, "device", model="AC2003")
        )
        hint = DeviceProfileHint(
            transport="adb",
            identifier_sha256="e" * 64,
            result="PROFILE_HINT_ONLY",
            candidate_profile_id="oneplus/avicii",
            candidate_display_name="OnePlus Nord AC2003",
            profile_status="PLANNED_NOT_SUPPORTED",
            evidence=("adb_model_matches_profile_allowlist",),
        )

        rendered = render_device_inventory(_App(), evidence, (hint,))  # type: ignore[arg-type]

        self.assertIn("HINT:OnePlus Nord AC2003:oneplus/avicii:PLANNED_NOT_SUPPORTED", rendered)

    def test_ambiguous_profile_hint_never_displays_a_candidate(self) -> None:
        evidence = _evidence(DeviceObservation("adb", "f" * 64, "device", model="AC2003"))
        hint = DeviceProfileHint(
            transport="adb",
            identifier_sha256="f" * 64,
            result="AMBIGUOUS_PROFILE_HINT",
            candidate_profile_id=None,
            candidate_display_name=None,
            profile_status=None,
            evidence=(),
        )

        rendered = render_device_inventory(_App(), evidence, (hint,))  # type: ignore[arg-type]

        self.assertIn("AMBIGUOUS", rendered)
        self.assertNotIn("oneplus/avicii", rendered)
