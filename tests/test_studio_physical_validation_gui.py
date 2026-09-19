from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from swirphoneos.i18n import translate
from swirphoneos.studio import Studio
from swirphoneos.studio_evidence import StudioEvidenceError


class _Value:
    def __init__(self, value: str):
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _StateButton:
    def __init__(self) -> None:
        self.changes: list[tuple[str, ...]] = []

    def state(self, values: list[str]) -> None:
        self.changes.append(tuple(values))


def _summary() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": "swirphoneos_studio_physical_validation_summary",
        "validation_session_id": "avicii-physical-studio-gui-001",
        "profile_id": "oneplus/avicii",
        "device_model": "AC2003",
        "device_codename": "avicii",
        "target_build": "Swir/test/build",
        "support_candidate_review_ready": True,
        "known_capability_failures": ["camera"],
        "missing_requirements": ["physical_restore_proof"],
        "support_status": "NOT_SUPPORTED",
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
        "evidence_sha256": "a" * 64,
    }


def _app(*, busy: bool = False) -> Studio:
    app = object.__new__(Studio)
    app.root = object()
    app.session = SimpleNamespace(busy=busy, report=None)
    app.language = _Value("en")
    app.readiness_summary = {"stale": True}
    app.support_summary = {"stale": True}
    app.physical_summary = None
    app.status_key = "ready"
    app.save = _StateButton()
    app._labels = []
    app.started = 0.0
    app.show_report = lambda text: setattr(app, "_shown", text)
    app.update_status = lambda: None
    return app


class StudioPhysicalValidationGuiBridgeTests(unittest.TestCase):
    def test_review_action_loads_only_bounded_summary_and_never_exports_it(self):
        app = _app()
        summary = _summary()
        with patch(
            "swirphoneos.studio.filedialog.askopenfilename",
            return_value="/tmp/physical-validation.json",
        ) as dialog, patch(
            "swirphoneos.studio.load_public_device_physical_validation_summary",
            return_value=summary,
        ) as loader:
            Studio.open_physical_validation(app)

        dialog.assert_called_once()
        loader.assert_called_once_with(Path("/tmp/physical-validation.json"))
        self.assertIs(app.physical_summary, summary)
        self.assertIsNone(app.readiness_summary)
        self.assertIsNone(app.support_summary)
        self.assertEqual(app.status_key, "device_validation_loaded")
        self.assertIn(("disabled",), app.save.changes)
        self.assertIn("oneplus/avicii", app._shown)
        self.assertIn(translate("en", "device_capability_camera"), app._shown)
        self.assertNotIn("hardware_evidence_sha256", app._shown)

        app.session.report = object()
        with patch("swirphoneos.studio.filedialog.asksaveasfilename") as save_dialog:
            Studio.export_report(app)
        save_dialog.assert_not_called()

    def test_review_action_is_unavailable_while_diagnostics_are_busy(self):
        app = _app(busy=True)
        with patch("swirphoneos.studio.filedialog.askopenfilename") as dialog:
            Studio.open_physical_validation(app)
        dialog.assert_not_called()
        self.assertIsNone(app.physical_summary)

    def test_invalid_review_fails_closed_without_leaking_loader_details(self):
        app = _app()
        with patch(
            "swirphoneos.studio.filedialog.askopenfilename",
            return_value="/private/physical-validation.json",
        ), patch(
            "swirphoneos.studio.load_public_device_physical_validation_summary",
            side_effect=StudioEvidenceError("private-token"),
        ), patch("swirphoneos.studio.messagebox.showerror") as error:
            Studio.open_physical_validation(app)

        error.assert_called_once()
        self.assertNotIn("private-token", str(error.call_args))
        self.assertIsNone(app.physical_summary)
        self.assertEqual(app.status_key, "ready")

    def test_language_refresh_rerenders_loaded_physical_summary(self):
        app = _app()
        app.physical_summary = _summary()
        app.readiness_summary = None
        app.support_summary = None
        app.language.set("pl")
        Studio.refresh_language(app)
        self.assertIn(translate("pl", "device_capability_camera"), app._shown)
        self.assertIn("oneplus/avicii", app._shown)


if __name__ == "__main__":
    unittest.main()
