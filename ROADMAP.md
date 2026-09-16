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

The read-only ADB CLI, Fastboot/FastbootD inspection, strict schema-v1 profile registry and first SwirPhoneStudio GUI are slices of `desktop_diagnostics`, not completion of its 8-point gate. Foundation evidence: `ARCHITECTURE.md`, `BETA_RELEASE_GATE.md`, `swirphoneos/readiness.py`, `tests/test_readiness.py` and the results recorded in `BUILD_STATUS.md`.

## Next engineering work

Harden **SwirPhoneStudio** into a reproducible Windows package: add packaging metadata/build workflow, connect the existing project icon to the packaged executable, add startup/error-path smoke tests and keep OS-language detection with English fallback. Perform real Windows/USB ADB + Fastboot/FastbootD smoke tests when reference hardware is available; only then can `desktop_diagnostics` be considered for completion.

In parallel, select and pin the upstream AOSP baseline after checking actual build-resource requirements and vendor constraints. Add bounded source/environment preflight and reproducible build metadata without starting an unbounded source download. Then target an emulator boot before claiming any GSI or physical-phone support.

The profile schema must evolve from metadata-only to an independently verified installation-plan format only after recovery/rollback contracts exist. No generic write operation may be enabled merely because a device reports Treble, a codename or an unlocked bootloader.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: all mandatory `BETA_RELEASE_GATE.md` checks passed for the exact release candidate. Stable: stricter sustained runtime, update, recovery and security validation.

Device expansion follows evidence, not manufacturer checklists. GSI, device-pack and full-port support are separate strategies. Unsupported or permanently locked devices remain unsupported rather than getting a risky generic flash script.
