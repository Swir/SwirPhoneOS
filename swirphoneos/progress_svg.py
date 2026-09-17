"""Deterministic SWIR Progress SVG PRO assets derived from ``project.json``.

The authoritative project-completion calculation remains the weighted milestone
ledger validated by :mod:`swirphoneos.readiness`. Beta readiness is reported as
a separate gate counter and is never inferred from the engineering percentage.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable

from .readiness import evaluate, load_ledger

PROJECT_NAME = "SwirPhoneOS"
SCOPE_LABEL = "Weighted engineering progress"
LEDGER_RELATIVE_PATH = Path("project.json")
CARD_RELATIVE_PATH = Path("assets/readme/progress-card.svg")
MINI_RELATIVE_PATH = Path("assets/readme/progress-mini.svg")
TEMPLATE_RELATIVE_PATH = Path("assets/readme/progress-template.svg")
CALCULATION_METHOD = "sum(weight for evidence-complete milestones) / 100 weighted points"
CARD_TRACK_X = 50.0
CARD_TRACK_WIDTH = 1100.0
MINI_TRACK_X = 170.0
MINI_TRACK_WIDTH = 700.0


@dataclass(frozen=True)
class ProgressSnapshot:
    project_name: str
    scope_label: str
    weighted_percent: float
    completed_milestones: int
    total_milestones: int
    beta_gates_passed: int
    beta_gates_total: int
    beta_release_allowed: bool

    @property
    def fraction(self) -> float:
        return max(0.0, min(1.0, self.weighted_percent / 100.0))

    @property
    def project_status(self) -> str:
        return "COMPLETE" if self.weighted_percent >= 100.0 else "IN PROGRESS"

    @property
    def beta_status(self) -> str:
        return "BETA READY" if self.beta_release_allowed else "NOT BETA READY"


def snapshot_from_ledger(path: Path) -> ProgressSnapshot:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Project ledger must be a regular non-symlink file.")
    result = evaluate(load_ledger(path))
    return ProgressSnapshot(
        project_name=PROJECT_NAME,
        scope_label=SCOPE_LABEL,
        weighted_percent=float(result["progress_percent"]),
        completed_milestones=int(result["completed_milestones"]),
        total_milestones=int(result["total_milestones"]),
        beta_gates_passed=int(result["beta_gates_passed"]),
        beta_gates_total=int(result["beta_gates_total"]),
        beta_release_allowed=bool(result["beta_release_allowed"]),
    )


def _number(value: float) -> str:
    rounded = round(value, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def _percent(value: float) -> str:
    rounded = round(value, 1)
    if rounded == int(rounded):
        return f"{int(rounded)}%"
    return f"{rounded:.1f}%"


def _wrap_label(label: str, limit: int = 58) -> tuple[str, ...]:
    normalized = " ".join(label.split())
    if len(normalized) <= limit:
        return (normalized,)
    split_at = normalized.rfind(" ", 0, limit + 1)
    if split_at <= 0:
        split_at = limit
    first = normalized[:split_at].strip()
    second = normalized[split_at:].strip()
    return (first, second)


def _svg_shell(width: int, height: int, title: str, description: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
    <linearGradient id="swir-progress" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0088FF"/>
      <stop offset="1" stop-color="#62E5FF"/>
    </linearGradient>
    <pattern id="swir-grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#143044" stroke-width="1" opacity="0.22"/>
    </pattern>
    <filter id="swir-glow" x="-20%" y="-200%" width="140%" height="500%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
{body}
</svg>
'''


def _render_unknown_card(project_name: str = PROJECT_NAME, scope_label: str = SCOPE_LABEL) -> str:
    body = f'''  <rect x="1" y="1" width="1198" height="178" rx="22" fill="#02050A" stroke="#17364A" stroke-width="2"/>
  <rect x="2" y="2" width="1196" height="176" rx="21" fill="url(#swir-grid)" opacity="0.55"/>
  <text x="50" y="34" fill="#62E5FF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700" letter-spacing="1.6">SWIR PROJECT • {escape(project_name)}</text>
  <text x="50" y="68" fill="#F4FAFF" font-size="24" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{escape(scope_label)}</text>
  <text x="1150" y="68" text-anchor="end" fill="#F4FAFF" font-size="32" font-family="Segoe UI, Arial, sans-serif" font-weight="800">N/A</text>
  <text x="50" y="92" fill="#8DA8B8" font-size="14" font-family="Segoe UI, Arial, sans-serif">PLANNING • authoritative scope unavailable</text>
  <rect id="progress-track" x="50" y="104" width="1100" height="18" rx="9" fill="#07111C" stroke="#1D4258"/>
  <text x="50" y="151" fill="#F4FAFF" font-size="15" font-family="Segoe UI, Arial, sans-serif">Milestones: N/A</text>
  <text x="1150" y="151" text-anchor="end" fill="#8DA8B8" font-size="15" font-family="Segoe UI, Arial, sans-serif">Beta gates: N/A</text>'''
    return _svg_shell(1200, 180, f"{project_name} progress — N/A", "No verified project progress denominator is available; progress is N/A.", body)


def render_card(snapshot: ProgressSnapshot | None) -> str:
    if snapshot is None:
        return _render_unknown_card()
    label_lines = _wrap_label(snapshot.scope_label)
    expanded = len(label_lines) > 1
    height = 212 if expanded else 180
    label_y = 66 if not expanded else 62
    status_y = 92 if not expanded else 116
    track_y = 104 if not expanded else 128
    footer_y = 151 if not expanded else 183
    percent_y = 68 if not expanded else 81
    percent_text = _percent(snapshot.weighted_percent)
    fill_width = CARD_TRACK_WIDTH * snapshot.fraction
    fill = ""
    if fill_width > 0:
        fill = (
            f'  <rect id="progress-fill" x="{_number(CARD_TRACK_X)}" y="{track_y}" '
            f'width="{_number(fill_width)}" height="18" rx="9" fill="url(#swir-progress)" '
            'filter="url(#swir-glow)" clip-path="url(#card-track-clip)"/>\n'
        )
    label_nodes = []
    for index, line in enumerate(label_lines):
        label_nodes.append(
            f'  <text x="50" y="{label_y + index * 29}" fill="#F4FAFF" font-size="24" '
            f'font-family="Segoe UI, Arial, sans-serif" font-weight="700">{escape(line)}</text>'
        )
    title = f"{snapshot.project_name} — {snapshot.scope_label}: {percent_text}"
    milestone_verb = "is" if snapshot.completed_milestones == 1 else "are"
    desc = (
        f"Verified weighted engineering progress is {percent_text}; "
        f"{snapshot.completed_milestones} of {snapshot.total_milestones} milestones {milestone_verb} complete. "
        f"Beta readiness is {snapshot.beta_gates_passed} of {snapshot.beta_gates_total} gates passed and {snapshot.beta_status}."
    )
    body = f'''  <defs>
    <clipPath id="card-track-clip"><rect x="50" y="{track_y}" width="1100" height="18" rx="9"/></clipPath>
  </defs>
  <rect x="1" y="1" width="1198" height="{height - 2}" rx="22" fill="#02050A" stroke="#17364A" stroke-width="2"/>
  <rect x="2" y="2" width="1196" height="{height - 4}" rx="21" fill="url(#swir-grid)" opacity="0.55"/>
  <text x="50" y="34" fill="#62E5FF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700" letter-spacing="1.6">SWIR PROJECT • {escape(snapshot.project_name)}</text>
{chr(10).join(label_nodes)}
  <text x="1150" y="{percent_y}" text-anchor="end" fill="#F4FAFF" font-size="32" font-family="Segoe UI, Arial, sans-serif" font-weight="800">{percent_text}</text>
  <text x="50" y="{status_y}" fill="#8DA8B8" font-size="14" font-family="Segoe UI, Arial, sans-serif">{snapshot.project_status} • authoritative source: project.json • weighted milestone model</text>
  <rect id="progress-track" x="50" y="{track_y}" width="1100" height="18" rx="9" fill="#07111C" stroke="#1D4258"/>
{fill}  <text x="50" y="{footer_y}" fill="#F4FAFF" font-size="15" font-family="Segoe UI, Arial, sans-serif">Milestones: {snapshot.completed_milestones}/{snapshot.total_milestones} complete</text>
  <text x="1150" y="{footer_y}" text-anchor="end" fill="#8DA8B8" font-size="15" font-family="Segoe UI, Arial, sans-serif">Beta gates: {snapshot.beta_gates_passed}/{snapshot.beta_gates_total} passed • {snapshot.beta_status}</text>'''
    return _svg_shell(1200, height, title, desc, body)


def render_mini(snapshot: ProgressSnapshot | None) -> str:
    if snapshot is None:
        body = '''  <rect x="1" y="1" width="898" height="70" rx="16" fill="#02050A" stroke="#17364A" stroke-width="2"/>
  <rect x="2" y="2" width="896" height="68" rx="15" fill="url(#swir-grid)" opacity="0.45"/>
  <text x="20" y="27" fill="#62E5FF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700">SwirPhoneOS</text>
  <text x="20" y="50" fill="#8DA8B8" font-size="12" font-family="Segoe UI, Arial, sans-serif">Milestones: N/A</text>
  <rect id="progress-track" x="170" y="28" width="700" height="14" rx="7" fill="#07111C" stroke="#1D4258"/>
  <text x="870" y="19" text-anchor="end" fill="#F4FAFF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700">N/A</text>
  <text x="870" y="61" text-anchor="end" fill="#8DA8B8" font-size="12" font-family="Segoe UI, Arial, sans-serif">Beta gates: N/A</text>'''
        return _svg_shell(900, 72, "SwirPhoneOS progress — N/A", "No verified project progress denominator is available; progress is N/A.", body)
    percent_text = _percent(snapshot.weighted_percent)
    fill_width = MINI_TRACK_WIDTH * snapshot.fraction
    fill = ""
    if fill_width > 0:
        fill = (
            f'  <rect id="progress-fill" x="{_number(MINI_TRACK_X)}" y="28" '
            f'width="{_number(fill_width)}" height="14" rx="7" fill="url(#swir-progress)" '
            'filter="url(#swir-glow)" clip-path="url(#mini-track-clip)"/>\n'
        )
    title = f"{snapshot.project_name} roadmap progress: {percent_text}"
    desc = (
        f"Weighted engineering progress {percent_text}; milestones {snapshot.completed_milestones} of {snapshot.total_milestones}; "
        f"beta gates {snapshot.beta_gates_passed} of {snapshot.beta_gates_total}."
    )
    body = f'''  <defs>
    <clipPath id="mini-track-clip"><rect x="170" y="28" width="700" height="14" rx="7"/></clipPath>
  </defs>
  <rect x="1" y="1" width="898" height="70" rx="16" fill="#02050A" stroke="#17364A" stroke-width="2"/>
  <rect x="2" y="2" width="896" height="68" rx="15" fill="url(#swir-grid)" opacity="0.45"/>
  <text x="20" y="27" fill="#62E5FF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{escape(snapshot.project_name)}</text>
  <text x="20" y="50" fill="#8DA8B8" font-size="12" font-family="Segoe UI, Arial, sans-serif">Milestones: {snapshot.completed_milestones}/{snapshot.total_milestones}</text>
  <rect id="progress-track" x="170" y="28" width="700" height="14" rx="7" fill="#07111C" stroke="#1D4258"/>
{fill}  <text x="870" y="19" text-anchor="end" fill="#F4FAFF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{percent_text}</text>
  <text x="870" y="61" text-anchor="end" fill="#8DA8B8" font-size="12" font-family="Segoe UI, Arial, sans-serif">{snapshot.project_status} • Beta {snapshot.beta_gates_passed}/{snapshot.beta_gates_total}</text>'''
    return _svg_shell(900, 72, title, desc, body)


def render_template() -> str:
    body = '''  <rect x="1" y="1" width="1198" height="178" rx="22" fill="#02050A" stroke="#17364A" stroke-width="2"/>
  <rect x="2" y="2" width="1196" height="176" rx="21" fill="url(#swir-grid)" opacity="0.55"/>
  <text x="50" y="34" fill="#62E5FF" font-size="15" font-family="Segoe UI, Arial, sans-serif" font-weight="700" letter-spacing="1.6">SWIR PROGRESS SVG PRO • TEMPLATE / NOT PROJECT DATA</text>
  <text x="50" y="68" fill="#F4FAFF" font-size="24" font-family="Segoe UI, Arial, sans-serif" font-weight="700">Authoritative measured scope goes here</text>
  <text x="1150" y="68" text-anchor="end" fill="#F4FAFF" font-size="32" font-family="Segoe UI, Arial, sans-serif" font-weight="800">N/A</text>
  <text x="50" y="92" fill="#8DA8B8" font-size="14" font-family="Segoe UI, Arial, sans-serif">PLANNING • bind this template to verified project data before use</text>
  <rect id="progress-track" x="50" y="104" width="1100" height="18" rx="9" fill="#07111C" stroke="#1D4258"/>
  <text x="50" y="151" fill="#F4FAFF" font-size="15" font-family="Segoe UI, Arial, sans-serif">Counter: N/A</text>
  <text x="1150" y="151" text-anchor="end" fill="#8DA8B8" font-size="15" font-family="Segoe UI, Arial, sans-serif">Release readiness: N/A</text>'''
    return _svg_shell(
        1200,
        180,
        "SWIR progress card template — not project data",
        "Reusable SWIR Progress SVG PRO template. Values are intentionally N/A and must not be presented as live project progress.",
        body,
    )


def expected_assets(root: Path) -> dict[Path, str]:
    snapshot = snapshot_from_ledger(root / LEDGER_RELATIVE_PATH)
    return {
        root / CARD_RELATIVE_PATH: render_card(snapshot),
        root / MINI_RELATIVE_PATH: render_mini(snapshot),
        root / TEMPLATE_RELATIVE_PATH: render_template(),
    }


def sync_assets(root: Path, *, check: bool) -> list[Path]:
    stale: list[Path] = []
    for path, expected in expected_assets(root).items():
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError("Progress SVG output paths must not traverse symlinks.")
        if path.exists() and not path.is_file():
            raise ValueError("Progress SVG output path must be a regular file.")
        if path.exists() and path.read_text(encoding="utf-8") == expected:
            continue
        stale.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8", newline="\n")
    return stale


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or verify SwirPhoneOS progress SVG assets from project.json.")
    parser.add_argument("--check", action="store_true", help="Fail when committed SVG assets are stale or missing.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = args.root.resolve()
    stale = sync_assets(root, check=args.check)
    if args.check and stale:
        print("Progress SVG assets are stale: " + ", ".join(str(path.relative_to(root)) for path in stale))
        return 1
    if not args.check:
        if stale:
            print("Updated progress SVG assets: " + ", ".join(str(path.relative_to(root)) for path in stale))
        else:
            print("Progress SVG assets already match project.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
