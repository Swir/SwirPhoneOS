"""Synthetic host tests; none are evidence of a working physical phone."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from swirphoneos.__main__ import main
from swirphoneos.preflight import MAX_JSON_BYTES, DeviceProfile, assess, load_json

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "device_packs/oneplus/avicii/profile.json"
SNAPSHOT = ROOT / "examples/avicii-properties.SYNTHETIC.json"


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.raw = load_json(PROFILE)
        self.profile = DeviceProfile.from_dict(self.raw)
        self.props = load_json(SNAPSHOT)

    def test_matching_hints_never_allow_writes(self):
        result = assess(self.props, self.profile)
        self.assertTrue(result.identity_hint_matches)
        self.assertTrue(result.architecture_hint_matches)
        self.assertFalse(result.write_operations_allowed)
        self.assertIn("WRITE_BACKEND_NOT_IMPLEMENTED", result.blockers)

    def test_missing_properties_fail_closed(self):
        result = assess({}, self.profile)
        self.assertFalse(result.identity_hint_matches)
        self.assertIsNone(result.treble_hint)
        self.assertIsNone(result.unlocked_hint)
        self.assertEqual(len(result.blockers), 10)

    def test_wrong_model_or_codename_rejected(self):
        for key in ("ro.product.model", "ro.product.device"):
            with self.subTest(key=key):
                props = {**self.props, key: "OTHER"}
                self.assertFalse(assess(props, self.profile).identity_hint_matches)

    def test_architecture_requires_exact_token(self):
        self.props["ro.product.cpu.abilist"] = "fake-arm64-v8a"
        self.assertFalse(assess(self.props, self.profile).architecture_hint_matches)

    def test_unknown_is_not_unlocked(self):
        for value in (None, "", "false", "unknown", "2"):
            with self.subTest(value=value):
                self.props["ro.boot.flash.locked"] = value
                self.assertIsNone(assess(self.props, self.profile).unlocked_hint)

    def test_locked_hint(self):
        self.props["ro.boot.flash.locked"] = "1"
        self.assertIs(assess(self.props, self.profile).unlocked_hint, False)

    def test_false_treble_is_false(self):
        self.props["ro.treble.enabled"] = "false"
        self.assertIs(assess(self.props, self.profile).treble_hint, False)

    def test_bad_property_types_rejected(self):
        for value in (True, 0, [], {}, "a\n", "x" * 4097):
            with self.subTest(value=type(value).__name__):
                self.props["ro.treble.enabled"] = value
                with self.assertRaises(ValueError):
                    assess(self.props, self.profile)

    def test_report_does_not_export_serial(self):
        self.props["ro.serialno"] = "PRIVATE_TEST_SERIAL"
        self.assertNotIn("PRIVATE_TEST_SERIAL", json.dumps(assess(self.props, self.profile).to_dict()))

    def test_profile_cannot_claim_full_support(self):
        self.raw["support_status"] = "FULL"
        with self.assertRaises(ValueError):
            DeviceProfile.from_dict(self.raw)

    def test_invalid_profile_schema_or_fields(self):
        for change in ({"schema_version": True}, {"schema_version": 2}, {"extra": 1},
                       {"models": []}, {"models": ["AC2003", "AC2003"]}, {"id": "../bad"}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    DeviceProfile.from_dict({**self.raw, **change})

    def test_inputs_unchanged(self):
        before = copy.deepcopy(self.props)
        assess(self.props, self.profile)
        self.assertEqual(self.props, before)

    def test_json_rejects_ambiguous_or_invalid_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for content in (b'{"a": 1, "a": 2}', b'{"a": NaN}', b'[]', b'\xff', b'{'):
                path.write_bytes(content)
                with self.subTest(content=content):
                    with self.assertRaises(ValueError):
                        load_json(path)

    def test_json_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
            with self.assertRaises(ValueError):
                load_json(path)

    def test_cli_reports_blocked_and_exit_two(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--profile", str(PROFILE), "--snapshot", str(SNAPSHOT)])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["write_operations_allowed"])

    def test_cli_invalid_file_has_sanitized_error(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            code = main(["--profile", str(PROFILE), "--snapshot", "/missing/PRIVATE_TEST_PATH"])
        self.assertEqual(code, 1)
        self.assertNotIn("PRIVATE_TEST_PATH", output.getvalue())


if __name__ == "__main__":
    unittest.main()
