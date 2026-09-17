# SwirPhoneOS progress SVG contract

SwirPhoneOS implements **SWIR Progress SVG PRO v1** with generated local assets under `assets/readme/`.

## Authoritative source

The only project-completion source used by the generator is the root [`project.json`](../project.json) ledger validated by `swirphoneos.readiness`.

The project percentage preserves the existing weighted engineering model:

```text
weighted progress = sum(weight for evidence-complete milestones) / 100 weighted points
```

At the current ledger state, only `foundation` is complete and it carries weight `2`, so project progress is **2%** even though the raw milestone counter is **1/10**. The raw counter is shown as a labelled counter only; it is never converted into an incorrect 10% progress claim.

Beta readiness is a separate scope. The SVGs show the passed beta-gate counter from the same evaluated ledger, but weighted engineering progress cannot make the project beta-ready. `BETA READY` may only be shown when the actual release authorization result permits it.

## Generated assets

- `assets/readme/progress-card.svg` — full project card embedded near README project status.
- `assets/readme/progress-mini.svg` — compact companion embedded in the authoritative roadmap dashboard.
- `assets/readme/progress-template.svg` — reusable local visual template marked `TEMPLATE / NOT PROJECT DATA`; it is never embedded as live progress.

All assets are self-contained SVG/XML with no script, remote image, external font or tracking dependency. The palette follows the SWIR dark/electric-cyan family: `#02050A`, `#07111C`, `#0088FF`, `#62E5FF`, `#F4FAFF` and `#8DA8B8`.

## Generate or verify

From the repository root:

```sh
python -m swirphoneos.progress_svg
python -m swirphoneos.progress_svg --check
```

Normal generation rewrites only stale generated SVG files. `--check` is read-only and exits non-zero when a committed asset is missing or differs from the deterministic output for the current ledger.

The unit suite also runs this freshness check, so changing `project.json` without regenerating the graphics fails host CI instead of leaving a contradictory README percentage.

## Geometry and fail-closed rules

The full card uses the standard 1100 px progress track and the mini uses the standard 700 px track. Fill width is calculated from the unrounded weighted fraction and clipped to the track. Zero progress omits the fill/glow entirely; 100% cannot exceed the track. Long measured-scope labels expand the card rather than colliding with status text.

Unknown or unavailable scope renders as **N/A**, never fabricated `0%` or `100%`. A malformed authoritative ledger is rejected by the existing project-ledger validator rather than converted into a decorative progress value.

The generator rejects symlinked output paths and does not weaken roadmap markers, release gates, device-support policy, SwirRoot safety rules or README PRO v2 requirements.

## Current truthful state

The generated project card currently represents:

- weighted engineering progress: **2%**;
- completed milestones: **1/10**;
- beta gates passed: **0/9**;
- beta state: **NOT BETA READY**.

These values do not claim an AOSP build, Cuttlefish boot, working GSI, supported physical phone, safe installer, functional root backend or beta release.
