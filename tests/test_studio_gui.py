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
        self.assertIn("SwirPhoneOS", self.root.title())

    def test_success_shows_report(self):
        self.app.start_scan()
        self.complete_scan()
        self.assertIn("SYNTHETIC TEST ONLY", self.app.report.get("1.0", "end"))
        self.assertTrue(self.app.save.instate(["!disabled"]))
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
        for lang in ("pl", "nb", "en"):
            self.app.language.set(lang)
            self.app.refresh_language()
            self.assertEqual(self.app.scan.cget("text"), translate(lang, "scan"))

    def test_minimum_window_keeps_report_and_footer(self):
        self.root.geometry("640x500")
        self.root.update()
        self.assertGreater(self.app.report.winfo_height(), 30)
        for widget, _ in self.app._labels:
            self.assertLess(widget.winfo_rooty() - self.root.winfo_rooty(), 500)

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
            self.app.close()
            self.assertTrue(self.app.closed)
        finally:
            release.set()
