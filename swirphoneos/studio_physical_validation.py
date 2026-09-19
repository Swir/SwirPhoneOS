"""Localized, read-only physical-device validation review for SwirPhoneStudio.

This module contains presentation helpers only. It never opens an Android SDK
transport, executes a process, writes to a phone, promotes a device profile or
turns review evidence into installation/root authorization.
"""
from __future__ import annotations

from pathlib import Path

from .i18n import CATALOGS, translate
from .studio_evidence import load_public_device_physical_validation_summary


def render_physical_validation_summary(summary: dict[str, object], language: str) -> str:
    """Render one bounded physical-validation summary in a supported host locale."""
    if language not in CATALOGS:
        language = "en"

    failures = summary["known_capability_failures"]
    if not isinstance(failures, list):
        raise ValueError("Physical validation summary capability failures are malformed.")
    failures_text = (
        ", ".join(translate(language, f"device_capability_{item}") for item in failures)
        if failures
        else translate(language, "none")
    )

    missing = summary["missing_requirements"]
    if not isinstance(missing, list):
        raise ValueError("Physical validation summary missing requirements are malformed.")
    # Missing requirement values are stable evidence-schema identifiers. Keeping
    # them verbatim preserves exact correspondence with machine-readable reports.
    missing_text = ", ".join(str(item) for item in missing) if missing else translate(language, "none")

    yes = translate(language, "yes")
    no = translate(language, "no")
    return translate(
        language,
        "device_validation_summary",
        session=summary["validation_session_id"],
        profile=summary["profile_id"],
        build=summary["target_build"],
        candidate=yes if summary["support_candidate_review_ready"] is True else no,
        failures=failures_text,
        missing=missing_text,
        support=yes if summary["support_claim_allowed"] is True else no,
        writes=yes if summary["device_write_allowed"] is True else no,
    )


def load_and_render_physical_validation(path: Path, language: str) -> tuple[dict[str, object], str]:
    """Load, validate and localize one absolute local report without device I/O."""
    summary = load_public_device_physical_validation_summary(path)
    return summary, render_physical_validation_summary(summary, language)
