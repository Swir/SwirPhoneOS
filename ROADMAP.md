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

A fail-closed build-provenance layer requires a real synchronized AOSP checkout, a fully pinned `repo manifest -r`, the exact `swirphoneos_cf_x86_64` product output, non-empty `boot.img` and `system.img`, and build identity from the produced `system/build.prop`. It hashes reviewed image artifacts and can bind that build evidence to a Cuttlefish report only when the runtime fingerprint exactly matches the built fingerprint. The resulting evidence bundle receives a canonical SHA-256 and never changes registry state automatically.

Cuttlefish runtime evidence requires `sys.boot_completed=1`, exact product/device/manufacturer identity, Android 17 / API 37, `userdebug`, build ID/fingerprint, every source-ready package and a launcher activity resolving inside each expected package. The manual-only self-hosted `aosp-build-evidence.yml` workflow can explicitly launch the exact built product, poll the strict runtime gate, launch-smoke every source-ready app, bind build/runtime fingerprints and always attempt local Cuttlefish cleanup. The launch-smoke runner is hard-gated on exact local SwirPhoneOS Cuttlefish identity and permits only package-local activity launch plus activity-state inspection; it is not a physical-device test path.

No completed source sync, Kati/Soong build or Cuttlefish boot exists yet, so `aosp_baseline` and `emulator_boot` remain incomplete. This automation closes orchestration gaps; it does not itself satisfy a runtime milestone.

### Android application source

Ten applications are now **`ANDROID_SOURCE`** and included in the Cuttlefish product: SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate, SwirPrivacy, SwirClock, SwirNotes, SwirCalendar and SwirRoot.

SwirRoot is now a meaningful Android source-stage control surface rather than a host-only contract. It has an original localized owner UI, a non-exported status/diagnostic service, current-build fingerprint display, a bounded app-private review audit, and a pure-Java enable/unroot gate policy. The checked-in Android service hard-disables its mutation backend and supported-build switch, reports `UNAVAILABLE`, and only reviews safety prerequisites after explicit owner confirmation. No `su`, process-execution, boot-image modification, partition write, unlock, flash or exploit path exists. Source-implemented capabilities are intentionally limited to `root_state` and `authorization_audit`; `guided_enable` and `guided_unroot` remain future capabilities that require an exact physically verified backend plus rollback/recovery evidence.

Source validation now scans every production Java file, not only the primary activity/policy pair, for forbidden execution/network/storage primitives. The SwirRoot contract additionally requires exact-build/profile/owner/rollback/journal/update-state gates and hard-disabled mutation support. All ten apps have eight locale resource sets including Arabic/RTL and dependency-free host tests for reviewed pure-Java logic where applicable.

All ten remain below `ANDROID_RUNTIME`. Source-only work therefore receives no weighted gate credit. Current intentional gaps also include Calculator scientific math, Update staged/recovery state, Privacy live indicators/access history and Calendar provider bridging.

### Desktop and SwirRoot

Read-only ADB/Fastboot/FastbootD diagnostics, multilingual SwirPhoneStudio and Windows developer packaging exist, but real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing. SwirRoot Android source is now present, but there is still no exact-build mutation implementation, supported root build, physical enable/unroot path, recovery proof or per-app privileged authorization backend.

## System app delivery track

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the built Android image.
- [ ] Settings, Files, Update, Privacy and Device Care usable with real runtime/platform state.
- [ ] Clock, Calculator, Notes, Calendar and SwirRoot built and exercised inside SwirPhoneOS Cuttlefish.
- [ ] Runtime accessibility, RTL and locale-switch review for all source-ready apps.

> Source progress: ten apps contain meaningful Android source and host-tested policy/logic, but the checkboxes stay open until they are built and exercised in the SwirPhoneOS image.

### Reference-hardware phase

- [ ] Swir Phone/Contacts/Messages validated against the exact reference telephony stack.
- [ ] Swir Camera/Gallery validated against the exact reference camera/media stack.
- [ ] Swir Recorder validated with the reference audio stack.
- [ ] Swir Backup/restore aligned with exact encryption/storage/recovery behavior.
- [ ] Calendar provider bridge, Browser, Weather and Swir Apps integrated to beta-appropriate quality.

### SwirRoot phase

- [x] Source-ready permission-free owner UI/service foundation with `UNAVAILABLE` default, explicit confirmation and fail-closed policy review.
- [ ] Authoritative ROOT OFF / ROOT ON / UNAVAILABLE state for an exact physically verified build/profile.
- [ ] Enable-root requires exact supported build/profile, owner confirmation, verified rollback material, durable transaction journaling and safe update state.
- [ ] Unroot restores the expected non-root boot/system state on the exact build/profile.
- [ ] Per-app root authorization is deny-by-default, revocable and auditable through a real privileged backend.
- [ ] SwirRoot integrates with Swir Update, recovery and SwirPhoneStudio.
- [ ] Physical enable → reboot → use → disable → recovery validation before any beta root claim.

## Next engineering work

1. Provision or attach a capable dedicated Linux x86-64 runner labeled `swir-aosp-builder`, set `SWIR_AOSP_WORKSPACE`, ensure Cuttlefish host prerequisites plus the trusted absolute `adb` path exist, and run the manual `AOSP build evidence` workflow with runtime collection enabled. It must initialize/sync exact `android-17.0.0_r1`, preserve `repo manifest -r`, stage the bounded `vendor/swir/` bundle and compile `swirphoneos_cf_x86_64-aosp_current-userdebug`.
2. Preserve the resulting `build-evidence.json`, `runtime-evidence.json`, `app-smoke-evidence.json` and `evidence-bundle.json`. The exact built fingerprint must match the booted fingerprint and all ten source-ready launchers, including SwirRoot, must successfully become resumed foreground activities before any runtime review.
3. Perform focused interactive checks that launch-smoke cannot prove: Settings/Files/Update/Privacy/DeviceCare flows, Notes/Calendar persistence/export, Clock timer/alarm hand-off, SwirRoot's fail-closed state/confirmation/audit UI, accessibility, text expansion, locale switching and Arabic RTL. Only then review any `ANDROID_RUNTIME` promotion.
4. Fix any real Kati/Soong/Android runtime regressions before expanding more app source. Runtime evidence has higher priority than increasing the app count.
5. Continue SwirPhoneStudio hardening; the next desktop gate evidence is actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device.
6. After emulator/GSI and recovery evidence, design a legitimate exact-build SwirRoot backend only for explicitly supported unlocked/owner-controlled device paths. Never bypass locked bootloaders, OEM protections or verification controls through exploits.
7. Expand device packs into reviewed installation/recovery plans only after exact-device evidence exists. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
