# SwirPhoneOS Roadmap

<!-- SWIR-ROADMAP-STANDARD:v1 -->
![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Roadmap](https://img.shields.io/badge/ROADMAP-2%25-blue)
![Done](https://img.shields.io/badge/DONE-1%2F10_milestones-blue)
![Status](https://img.shields.io/badge/STATUS-foundation-orange)

## Overall progress

**2% — weighted engineering milestones.**

`[--------------------] 2%`

| Completed milestones | Remaining | Total | Weighted progress |
| --- | --- | --- | --- |
| 1 | 9 | 10 | 2% |

The canonical ledger is `project.json`. Weights sum to 100; completion is the sum of weights for gates that are actually complete. One bar segment is 5 percentage points, rounded down. This is milestone accounting, not an estimate of elapsed work, remaining time or supported hardware. Beta readiness is tracked separately: **0/9 gates passed**.

| Gate | Weight | Completion evidence required |
| --- | ---: | --- |
| foundation | 2 | Architecture, explicit safety/release contracts, executable ledger validation and passing local negative tests |
| desktop_diagnostics | 8 | Tested read-only ADB/Fastboot/FastbootD diagnostics, profile validation, useful desktop UI and real Windows/USB smoke evidence |
| aosp_baseline | 10 | Pinned upstream manifest, reproducible environment and completed platform build |
| emulator_boot | 10 | Swir product boots into usable Android UI; recorded runtime and regression tests |
| gsi_validation | 10 | Built ARM64 GSI plus relevant Treble/VTS compatibility evidence and known-issues matrix |
| reference_hardware | 25 | Exact-model physical boot, firmware baseline, telephony/connectivity/audio/cameras/sensors/storage/charging/thermal/suspend/encryption validation |
| install_restore | 15 | User-confirmed safe installation and tested recovery/stock restore on the same device/firmware profile |
| swir_ux | 8 | Integrated launcher/SystemUI/settings, i18n, accessibility and visual/runtime review, not a static mockup |
| security_ota | 8 | Release signing, update authenticity, security review, tested update/rollback/recovery behavior |
| beta_release | 4 | All beta gates reviewed, actual images and Windows package published and post-release verified |

## Verified milestone checklist

- [x] foundation
- [ ] desktop_diagnostics
- [ ] aosp_baseline
- [ ] emulator_boot
- [ ] gsi_validation
- [ ] reference_hardware
- [ ] install_restore
- [ ] swir_ux
- [ ] security_ota
- [ ] beta_release

The read-only CLI and Flash Studio GUI are slices of desktop_diagnostics, not completion of its 8-point gate. The GUI has native-window tests, asynchronous inspection, EN/PL/NB catalogs and local report export. Fastboot/FastbootD, profile validation, packaged Windows delivery and real USB evidence remain outstanding. Foundation evidence: `ARCHITECTURE.md`, `BETA_RELEASE_GATE.md`, `swirphoneos/readiness.py`, `tests/test_readiness.py` and the test results recorded in `BUILD_STATUS.md`.

## Next engineering work

Select and pin an upstream AOSP baseline after checking actual build resources and vendor constraints. Implement a source/environment preflight without starting an unbounded download. Expand profile/schema and read-only Fastboot diagnostics with strict mode/identity handling, and integrate them into the existing GUI without enabling writes. Add Windows packaging and real local USB validation. No hardware milestone may be completed without physical test evidence.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: all mandatory `BETA_RELEASE_GATE.md` checks passed for the exact release candidate. Stable: stricter sustained runtime, update, recovery and security validation.

Device expansion follows evidence, not manufacturer checklists. GSI, device-pack and full-port support are separate strategies. Unsupported or permanently locked devices remain unsupported rather than getting a risky generic flash script.
