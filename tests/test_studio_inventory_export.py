"""Tests for deterministic, non-authoritative SwirPhoneStudio inventory exports."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from swirphoneos.studio_device_inventory import (
    DeviceInventoryEvidence,
    DeviceObservation,
    DeviceProfileHint,
)
from swirphoneos.studio_inventory_export import (
    build_inventory_bundle,
    serialize_inventory_bundle,
    write_inventory_bundle,
)


def _snapshot() -> tuple[DeviceInventoryEvidence, tuple[DeviceProfileHint, ...]]:
    observation = DeviceObservation(
        transport="adb",
        identifier_sha256="a" * 64,
        state="device",
        product="avicii",
        model="AC2003",
        device="avicii",
    )
    evidence = DeviceInventoryEvidence(
        observations=(observation,),
        adb_attempted=True,
        fastboot_attempted=False,
    )
    hint = DeviceProfileHint(
        transport="adb",
        identifier_sha256="a" * 64,
        result="PROFILE_HINT_ONLY",
        candidate_profile_id="oneplus/avicii",
        candidate_display_name="OnePlus Nord AC2003",
        profile_status="PLANNED_NOT_SUPPORTED",
        evidence=("adb_codename_matches_profile",),
    )
    return evidence, (hint,)


class StudioInventoryExportTests(TestCase):
    def test_bundle_is_explicitly_non_authoritative(self) -> None:
        evidence, hints = _snapshot()
        bundle = build_inventory_bundle(evidence, hints)

        self.assertEqual(bundle["kind"], "swirphoneos_read_only_device_inventory")
        self.assertIs(bundle["read_only"], True)
        self.assertIs(bundle["physical_verification"], False)
        self.assertIs(bundle["support_claim"], False)
        self.assertIs(bundle["flash_allowed"], False)
        self.assertIs(bundle["beta_gate_evidence"], False)
        self.assertEqual(bundle["inventory"]["observation_count"], 1)  # type: ignore[index]
        self.assertEqual(len(bundle["profile_hints"]), 1)  # type: ignore[arg-type]

    def test_serialization_is_deterministic_utf8_json(self) -> None:
        evidence, hints = _snapshot()
        first = serialize_inventory_bundle(evidence, hints)
        second = serialize_inventory_bundle(evidence, hints)

        self.assertEqual(first, second)
        decoded = json.loads(first.decode("utf-8"))
        self.assertEqual(decoded["schema_version"], 1)
        self.assertNotIn("raw_serial", first.decode("utf-8"))
        self.assertTrue(first.endswith(b"\n"))

    def test_export_is_create_only_and_hashes_exact_bytes(self) -> None:
        evidence, hints = _snapshot()
        with TemporaryDirectory() as directory:
            destination = Path(directory).resolve() / "inventory.json"
            digest = write_inventory_bundle(destination, evidence, hints)
            payload = destination.read_bytes()

            self.assertEqual(digest, sha256(payload).hexdigest())
            with self.assertRaises(FileExistsError):
                write_inventory_bundle(destination, evidence, hints)

    def test_export_rejects_relative_path(self) -> None:
        evidence, hints = _snapshot()
        with self.assertRaisesRegex(ValueError, "absolute"):
            write_inventory_bundle(Path("inventory.json"), evidence, hints)

    def test_bundle_rejects_detached_or_duplicate_profile_hints(self) -> None:
        evidence, hints = _snapshot()
        detached = DeviceProfileHint(
            transport="adb",
            identifier_sha256="b" * 64,
            result="NO_PROFILE_HINT",
            candidate_profile_id=None,
            candidate_display_name=None,
            profile_status=None,
            evidence=(),
        )
        with self.assertRaisesRegex(ValueError, "does not belong"):
            build_inventory_bundle(evidence, (detached,))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_inventory_bundle(evidence, (hints[0], hints[0]))


class StudioInventoryCliTests(TestCase):
    def test_headless_inventory_export_does_not_create_tk(self) -> None:
        from swirphoneos import studio_desktop

        evidence, hints = _snapshot()
        destination = Path("/tmp/swirphoneos-inventory.json")
        tool = Path("/reviewed/adb")
        with (
            patch.object(studio_desktop, "collect_inventory_snapshot", return_value=(evidence, hints)) as collect,
            patch.object(studio_desktop, "write_inventory_bundle", return_value="f" * 64) as write,
            patch.object(studio_desktop.tk, "Tk") as tk_root,
        ):
            result = studio_desktop.main(
                [
                    "--inventory-json",
                    str(destination),
                    "--transport",
                    "adb",
                    "--tool",
                    str(tool),
                ]
            )

        self.assertEqual(result, 0)
        collect.assert_called_once_with("adb", tool)
        write.assert_called_once_with(destination, evidence, hints)
        tk_root.assert_not_called()

    def test_partial_headless_arguments_fail_without_touching_device_or_gui(self) -> None:
        from swirphoneos import studio_desktop

        with (
            patch.object(studio_desktop, "collect_inventory_snapshot") as collect,
            patch.object(studio_desktop.tk, "Tk") as tk_root,
        ):
            result = studio_desktop.main(["--transport", "adb"])

        self.assertEqual(result, 2)
        collect.assert_not_called()
        tk_root.assert_not_called()
