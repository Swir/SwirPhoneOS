"""Fail-closed guard for SWIR progress presentation surfaces.

This checker complements ``swirphoneos.progress_svg``. The SVG generator owns
the progress math and asset bytes; this module prevents maintained Markdown
surfaces from re-introducing legacy character meters or embedding the wrong
live/template progress asset.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MAINTAINED_DOCS = ("README.md", "ROADMAP.md", "BUILD_STATUS.md")
CARD_REF = "assets/readme/progress-card.svg"
MINI_REF = "assets/readme/progress-mini.svg"
TEMPLATE_REF = "assets/readme/progress-template.svg"

# Deliberately narrow: reject progress-bar shapes, not Markdown checkboxes,
# horizontal rules, directory trees, tables or command examples.
LEGACY_BRACKET_METER = re.compile(
    r"\[(?:[#=\-█▓▒░■□▪▫]){5,}\](?:\s*\d+(?:\.\d+)?%)?"
)
LEGACY_GLYPH_METER = re.compile(
    r"(?:[█▓▒░■□▪▫]){3,}(?:\s*\d+(?:\.\d+)?%)?"
)


@dataclass(frozen=True)
class PresentationViolation:
    path: str
    reason: str


def _read_regular_utf8(root: Path, relative: str) -> str:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Maintained presentation surface must be a regular non-symlink file: {relative}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Maintained presentation surface must be strict UTF-8: {relative}") from exc


def _asset_count(text: str, asset: str) -> int:
    return text.count(asset)


def presentation_violations(root: Path) -> tuple[PresentationViolation, ...]:
    docs = {name: _read_regular_utf8(root, name) for name in MAINTAINED_DOCS}
    violations: list[PresentationViolation] = []

    for name, text in docs.items():
        if LEGACY_BRACKET_METER.search(text) or LEGACY_GLYPH_METER.search(text):
            violations.append(PresentationViolation(name, "legacy ASCII/Unicode progress meter found"))
        if TEMPLATE_REF in text:
            violations.append(PresentationViolation(name, "progress template must never be embedded as live project data"))

    readme = docs["README.md"]
    roadmap = docs["ROADMAP.md"]
    status = docs["BUILD_STATUS.md"]

    if _asset_count(readme, CARD_REF) != 1:
        violations.append(PresentationViolation("README.md", "README must embed progress-card.svg exactly once"))
    if _asset_count(readme, MINI_REF) != 0:
        violations.append(PresentationViolation("README.md", "README must not duplicate the roadmap mini graphic"))

    if _asset_count(roadmap, MINI_REF) != 1:
        violations.append(PresentationViolation("ROADMAP.md", "ROADMAP must embed progress-mini.svg exactly once"))
    if _asset_count(roadmap, CARD_REF) != 0:
        violations.append(PresentationViolation("ROADMAP.md", "ROADMAP must not duplicate the README card graphic"))

    if _asset_count(status, CARD_REF) or _asset_count(status, MINI_REF):
        violations.append(PresentationViolation("BUILD_STATUS.md", "BUILD_STATUS must not duplicate the authoritative README/ROADMAP graphics"))

    return tuple(violations)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SWIR SVG-only progress presentation surfaces.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        violations = presentation_violations(args.root.resolve())
    except ValueError as exc:
        print(f"SWIR progress presentation guard failed: {exc}")
        return 1
    if violations:
        for violation in violations:
            print(f"{violation.path}: {violation.reason}")
        return 1
    print("SWIR progress presentation guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
