from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path("platform/aosp_product/apps/SwirApps")
POLICY = ROOT / "src/org/swir/phoneos/apps/AppCatalogPolicy.java"
ACTIVITY = ROOT / "src/org/swir/phoneos/apps/MainActivity.java"
HOST_TEST = ROOT / "hosttest/AppCatalogPolicyHostTest.java"
MANIFEST = ROOT / "AndroidManifest.xml"


class SwirAppsUpdateProvenanceTests(unittest.TestCase):
    def test_update_provenance_is_local_read_only_and_owner_visible(self):
        policy = POLICY.read_text(encoding="utf-8")
        activity = ACTIVITY.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")

        for token in (
            "enum UpdateSource",
            "SYSTEM_IMAGE",
            "EXTERNAL_INSTALLER",
            "LOCAL_UNKNOWN",
            "updateSource",
            "normalizeUpdateTime",
            "validPackageName",
        ):
            self.assertIn(token, policy)

        for token in (
            "ApplicationInfo.FLAG_SYSTEM",
            "ApplicationInfo.FLAG_UPDATED_SYSTEM_APP",
            "PackageManager.GET_SIGNING_CERTIFICATES",
            "getInstallSourceInfo",
            "getInstallingPackageName",
            "lastUpdateTime",
            "DateFormat.getDateTimeInstance",
            "R.string.update_source_format",
            "R.string.last_updated_format",
            "Settings.ACTION_APPLICATION_DETAILS_SETTINGS",
        ):
            self.assertIn(token, activity)

        for forbidden in (
            "DownloadManager",
            "PackageInstaller",
            "ACTION_INSTALL_PACKAGE",
            "REQUEST_INSTALL_PACKAGES",
            "android.permission.INTERNET",
            "HttpURLConnection",
            "HttpsURLConnection",
            "java.net.",
        ):
            self.assertNotIn(forbidden, activity + "\n" + manifest)

    def test_policy_host_contract_compiles_and_runs_when_jdk_is_available(self):
        javac = shutil.which("javac")
        java = shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK is not available on this host")
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "classes"
            out.mkdir()
            subprocess.run(
                [javac, "-d", str(out), str(POLICY), str(HOST_TEST)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [java, "-cp", str(out), "org.swir.phoneos.apps.AppCatalogPolicyHostTest"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()
