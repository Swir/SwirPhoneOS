"""Native Tk smoke tests with synthetic inspection; no hardware or EXE claim."""
import os
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("SWIR_GUI_TESTS") == "1", "Enable SWIR_GUI_TESTS=1 on a graphical desktop.")
class GuiTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from swirphoneos.studio import Studio
        from swirphoneos.studio_state import DiagnosticSession
        from swirphoneos.diagnostics import summarize
        self.root = tk.Tk()
        self.app = Studio(self.root, DiagnosticSession(lambda _: summarize({"ro.product.model": "SYNTHETIC TEST ONLY"})))
        self.root.update()

    def tearDown(self):
        if not self.app.closed:
            self.app.close()

    def complete_scan(self):
        deadline = time.monotonic() + 3
        while self.app.session.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.session.busy)

    def test_launch_and_icon(self):
        self.assertEqual(self.app.icon.width(), 48)
        self.assertTrue(self.app.save.instate(["disabled"]))
        self.assertTrue(self.app.readiness.instate(["!disabled"]))
        self.assertIn("SwirPhoneOS", self.root.title())

    def test_success_shows_report(self):
        self.app.start_scan()
        self.complete_scan()
        self.assertIn("SYNTHETIC TEST ONLY", self.app.report.get("1.0", "end"))
        self.assertTrue(self.app.save.instate(["!disabled"]))
        self.assertTrue(self.app.readiness.instate(["!disabled"]))
        self.assertEqual(self.app.status_key, "done")

    def test_failure_clears_stale_export(self):
        from swirphoneos.diagnostics import DiagnosticError
        self.app.start_scan()
        self.complete_scan()
        def failure(_):
            raise DiagnosticError("private-path-and-serial")
        self.app.session._inspector = failure
        self.app.start_scan()
        self.complete_scan()
        self.assertTrue(self.app.save.instate(["disabled"]))
        self.assertNotIn("SYNTHETIC TEST ONLY", self.app.report.get("1.0", "end"))
        self.assertNotIn("private-path-and-serial", self.app.status.cget("text"))

    def test_language_switch(self):
        from swirphoneos.i18n import translate
        for lang in ("pl", "nb", "de", "es", "fr", "pt", "ar", "en"):
            self.app.language.set(lang)
            self.app.refresh_language()
            self.assertEqual(self.app.scan.cget("text"), translate(lang, "scan"))
            self.assertEqual(self.app.readiness.cget("text"), translate(lang, "review_readiness"))

    def test_readiness_review_is_display_only(self):
        from swirphoneos.i18n import translate
        summary = {
            "schema_version": 1,
            "source": "swirphoneos_studio_swirroot_readiness_summary",
            "action": "enable",
            "profile_id": "oneplus/avicii",
            "exact_build": "Swir/test/build",
            "transaction_id": "review-only",
            "missing_requirements": ["owner_confirmation", "verified_device_profile"],
            "policy_backend_available": False,
            "hardware_root_authorized": False,
            "transition_ready": False,
            "device_write_allowed": False,
        }
        with patch("swirphoneos.studio.filedialog.askopenfilename", return_value="/tmp/readiness.json"), \
             patch("swirphoneos.studio.load_public_swirroot_readiness_summary", return_value=summary):
            self.app.open_root_readiness()
        text = self.app.report.get("1.0", "end")
        self.assertIn("oneplus/avicii", text)
        self.assertIn(translate("en", "readiness_action_enable"), text)
        self.assertIn(translate("en", "readiness_gate_owner_confirmation"), text)
        self.assertNotIn("owner_confirmation", text)
        self.assertEqual(self.app.status_key, "readiness_loaded")
        self.assertTrue(self.app.save.instate(["disabled"]))
        self.assertIsNotNone(self.app.readiness_summary)

    def test_readiness_review_failure_is_private(self):
        from swirphoneos.studio_evidence import StudioEvidenceError
        with patch("swirphoneos.studio.filedialog.askopenfilename", return_value="/private/readiness.json"), \
             patch("swirphoneos.studio.load_public_swirroot_readiness_summary", side_effect=StudioEvidenceError("private-token")), \
             patch("swirphoneos.studio.messagebox.showerror") as error:
            self.app.open_root_readiness()
        error.assert_called_once()
        self.assertNotIn("private-token", str(error.call_args))
        self.assertIsNone(self.app.readiness_summary)

    def test_minimum_window_keeps_report_and_footer(self):
        self.root.geometry("640x500")
        for language in ("en", "pl", "nb"):
            with self.subTest(language=language):
                self.app.language.set(language)
                self.app.refresh_language()
                self.root.update()
                self.assertGreater(self.app.report.winfo_height(), 50)
                for widget, _ in self.app._labels:
                    bottom = widget.winfo_rooty() - self.root.winfo_rooty() + widget.winfo_height()
                    self.assertLessEqual(bottom, self.root.winfo_height())

    def test_no_save_dialog_without_report(self):
        with patch("swirphoneos.studio.filedialog.asksaveasfilename") as dialog:
            self.app.export_report()
            dialog.assert_not_called()

    def test_close_during_scan(self):
        from threading import Event
        from swirphoneos.diagnostics import summarize
        release = Event()
        def slow(_):
            release.wait(2)
            return summarize({})
        self.app.session._inspector = slow
        self.app.start_scan()
        try:
            self.assertTrue(self.app.readiness.instate(["disabled"]))
            self.app.close()
            self.assertTrue(self.app.closed)
        finally:
            release.set()
