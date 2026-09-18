from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
UPDATE_ROOT = ROOT / "platform" / "aosp_product" / "apps" / "SwirUpdate"
TRUST = UPDATE_ROOT / "src" / "org" / "swir" / "phoneos" / "update" / "OtaTrustStore.java"
DEFAULT = UPDATE_ROOT / "src" / "org" / "swir" / "phoneos" / "update" / "DefaultOtaTrustStore.java"
WORKFLOW = ROOT / ".github" / "workflows" / "essential-source-suite.yml"
DOC = ROOT / "docs" / "OTA_TRUST_STORE.md"


class SwirUpdateTrustStorePolicyTest(unittest.TestCase):
    def test_trust_store_lifecycle_is_explicit_and_fail_closed(self):
        text = TRUST.read_text(encoding="utf-8")
        self.assertIn("enum KeyStatus { ACTIVE, RETIRED, REVOKED }", text)
        self.assertIn("public static final int MAX_KEYS = 32", text)
        self.assertIn("REVOKED_KEY", text)
        self.assertIn("RETIRED_KEY", text)
        self.assertIn("CHANNEL_NOT_ALLOWED", text)
        self.assertIn("KEY_IDENTITY_INVALID", text)
        self.assertIn('"RSA".equalsIgnoreCase(publicKey.getAlgorithm())', text)
        self.assertIn("expectedSpkiSha256.equals(actualDigest)", text)
        self.assertIn("duplicate key id", text)
        self.assertIn("public boolean stagingAllowed() { return false; }", text)

    def test_default_store_has_no_implicit_production_trust_anchor(self):
        text = DEFAULT.read_text(encoding="utf-8")
        self.assertIn("return OtaTrustStore.empty();", text)
        self.assertNotIn("new OtaTrustStore.Entry", text)
        self.assertNotIn("BEGIN PUBLIC KEY", text)
        self.assertNotIn("BEGIN PRIVATE KEY", text)

    def test_production_updater_source_contains_no_private_signing_material_or_write_primitives(self):
        dangerous = (
            "BEGIN PRIVATE KEY",
            "BEGIN RSA PRIVATE KEY",
            "PrivateKey",
            "RecoverySystem.installPackage",
            "installPackage(",
            "reboot(",
            "fastboot",
            "/dev/block",
        )
        for source in (TRUST, DEFAULT):
            text = source.read_text(encoding="utf-8")
            for token in dangerous:
                with self.subTest(source=source.name, token=token):
                    self.assertNotIn(token, text)

    def test_ci_compiles_and_runs_trust_store_host_tests(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "OtaTrustStore.java",
            "DefaultOtaTrustStore.java",
            "OtaTrustStoreHostTest.java",
            "UpdatePolicyHostTest.java",
            "org.swir.phoneos.update.OtaTrustStoreHostTest",
            "org.swir.phoneos.update.UpdatePolicyHostTest",
        ):
            self.assertIn(required, text)

    def test_documentation_keeps_source_stage_boundary_explicit(self):
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("zero provisioned keys", text)
        self.assertIn("Private signing material must never", text)
        self.assertIn("AUTHENTIC_REVIEW_READY_NOT_STAGED", text)
        self.assertIn("stagingAllowed()", text)
        self.assertIn("does **not**", text)
        self.assertIn("physically verified supported device profile", text)


if __name__ == "__main__":
    unittest.main()
