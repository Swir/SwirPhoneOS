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

The canonical ledger is `project.json`. Weights total 100 and only evidence-complete gates contribute. Source scaffolding, host tests, provenance tooling and desktop packaging do not substitute for an Android build, boot or physical-device validation. Beta readiness remains **0/9 gates passed**.

| Gate | Weight | Completion evidence required |
| --- | ---: | --- |
| foundation | 2 | Architecture, safety/release contracts, executable ledger validation and negative tests |
| desktop_diagnostics | 8 | Tested read-only ADB/Fastboot/FastbootD diagnostics, profile validation, useful desktop UI and real Windows/USB smoke evidence |
| aosp_baseline | 10 | Pinned upstream manifest, reproducible environment and completed platform build |
| emulator_boot | 10 | Swir product boots into usable Android UI; recorded runtime and regression tests |
| gsi_validation | 10 | Built ARM64 GSI plus relevant Treble/VTS evidence and known-issues matrix |
| reference_hardware | 25 | Exact-model physical boot and validated telephony/connectivity/audio/cameras/sensors/storage/charging/thermal/suspend/encryption |
| install_restore | 15 | User-confirmed safe installation and tested recovery/stock restore on the same device/firmware profile |
| swir_ux | 8 | Integrated launcher/SystemUI/settings and essential Swir apps, i18n, accessibility and visual/runtime review |
| security_ota | 8 | Release signing, update authenticity, security review, tested update/rollback/recovery including SwirRoot interaction where enabled |
| beta_release | 4 | All beta gates reviewed, real images and Windows package published and post-release verified |

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

## Current engineering slices

### Platform, build provenance and runtime evidence

Android 17 / API 37 is pinned to `android-17.0.0_r1`. Exact-tag planning, build-host preflight, resolved-manifest SHA validation and bounded AOSP staging exist. The staging contract accepts independently reviewed JSON fragments while enforcing global uniqueness and the `vendor/swir/` destination boundary.

A new fail-closed build-provenance layer now requires a real synchronized AOSP checkout, a fully pinned `repo manifest -r`, the exact `swirphoneos_cf_x86_64` product output, non-empty `boot.img` and `system.img`, and build identity from the produced `system/build.prop`. It hashes reviewed image artifacts and can bind that build evidence to a Cuttlefish report only when the runtime fingerprint exactly matches the built fingerprint. The resulting evidence bundle receives a canonical SHA-256 and never changes registry state automatically.

Cuttlefish runtime evidence now requires `sys.boot_completed=1`, exact product/device/manufacturer identity, Android 17 / API 37, `userdebug`, build ID/fingerprint, every source-ready package and a launcher activity resolving inside each expected package. A manual-only self-hosted `aosp-build-evidence.yml` workflow now provides an executable exact-tag sync → stage → build → provenance path for a dedicated `swir-aosp-builder`. No completed source sync, Kati/Soong build or Cuttlefish boot exists yet, so `aosp_baseline` and `emulator_boot` remain incomplete.

### Android application source

Nine applications are now **`ANDROID_SOURCE`** and included in the Cuttlefish product: SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate, SwirPrivacy, SwirClock, SwirNotes and SwirCalendar.

Notes adds real offline SQLite CRUD/search, sharing and user-selected Markdown export. Calendar adds a local SQLite agenda, date/time editing, search, sharing and iCalendar export. Both are permission-free, have original SwirPhoneOS icons/UI, eight locale resource sets including Arabic/RTL and dependency-free host tests for their pure-Java policies. CalendarProvider bridging remains an explicit future capability and is rejected by source validation at this stage.

All nine remain below `ANDROID_RUNTIME`. Source-only work therefore receives no weighted gate credit. Current intentional gaps include Calculator scientific math, Update staged/recovery state, Privacy live indicators/access history and Calendar provider bridging.

### Desktop and SwirRoot

Read-only ADB/Fastboot/FastbootD diagnostics, multilingual SwirPhoneStudio and Windows developer packaging exist, but real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing. SwirRoot remains fail-closed: no exact-build root service, mutation path or physical enable/unroot/recovery evidence exists; supported root builds remain zero.

## System app delivery track

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the built Android image.
- [ ] Settings, Files, Update, Privacy and Device Care usable with real runtime/platform state.
- [ ] Clock, Calculator, Notes and Calendar built and exercised inside SwirPhoneOS Cuttlefish.
- [ ] Runtime accessibility, RTL and locale-switch review for all source-ready apps.

> Source progress: nine apps contain meaningful Android source and host-tested policy/logic, but the checkboxes stay open until they are built and exercised in the SwirPhoneOS image.

### Reference-hardware phase

- [ ] Swir Phone/Contacts/Messages validated against the exact reference telephony stack.
- [ ] Swir Camera/Gallery validated against the exact reference camera/media stack.
- [ ] Swir Recorder validated with the reference audio stack.
- [ ] Swir Backup/restore aligned with exact encryption/storage/recovery behavior.
- [ ] Calendar provider bridge, Browser, Weather and Swir Apps integrated to beta-appropriate quality.

### SwirRoot phase

- [ ] Authoritative ROOT OFF / ROOT ON / UNAVAILABLE state for the exact build/profile.
- [ ] Enable-root requires explicit support, owner confirmation, verified rollback material and journaling.
- [ ] Unroot restores the expected non-root boot/system state on the exact build/profile.
- [ ] Per-app root authorization is deny-by-default, revocable and auditable.
- [ ] SwirRoot integrates with Swir Update, recovery and SwirPhoneStudio.
- [ ] Physical enable → reboot → use → disable → recovery validation before any beta root claim.

## Next engineering work

1. Provision or attach a capable dedicated Linux x86-64 runner labeled `swir-aosp-builder`, set `SWIR_AOSP_WORKSPACE`, and run the manual `AOSP build evidence` workflow. It must initialize/sync exact `android-17.0.0_r1`, preserve `repo manifest -r`, stage the bounded `vendor/swir/` bundle and compile `swirphoneos_cf_x86_64-aosp_current-userdebug`.
2. Preserve `build-evidence.json` with artifact hashes and build fingerprint. Boot that exact product in Cuttlefish, capture schema-v3 runtime evidence and create `evidence-bundle.json`; fingerprint continuity must pass before any runtime claim.
3. Record interactive smoke results for all nine source-ready apps, accessibility, locale/RTL switching and core Settings/Files/Update/Privacy/DeviceCare flows. Only then review any `ANDROID_RUNTIME` promotion.
4. Fix any real Kati/Soong/Android runtime regressions before expanding more app source. Runtime evidence has higher priority than increasing the app count.
5. Continue SwirPhoneStudio hardening; the next desktop gate evidence is actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device.
6. After emulator/GSI evidence, expand device packs into reviewed installation/recovery plans. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
