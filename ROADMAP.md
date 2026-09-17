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

The canonical ledger is `project.json`. Weights total 100 and only evidence-complete gates contribute. Source scaffolding, host tests, provenance tooling, read-only hardware correlation, transaction preparation evidence and desktop packaging do not substitute for an Android build, boot or physical-device validation. Beta readiness remains **0/9 gates passed**.

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

The dedicated builder path now closes several evidence-continuity gaps before the first expensive real run. The workflow consumes the actual host-preflight schema (`checks[].id` / `checks[].passed`) and stops before source sync when mandatory checks fail or aggregate/check state is inconsistent. Staging records exact source/destination byte sizes and SHA-256 values, verifies copied bytes, and re-reads every staged file after Kati/Soong before build provenance can be accepted.

Build evidence requires a real synchronized AOSP checkout, a fully pinned `repo manifest -r`, exact `swirphoneos_cf_x86_64` output, non-empty `boot.img` and `system.img`, and a `system/build.prop` that matches the checked-in baseline for Android release, API level, build ID, security patch level and `userdebug` build type. Reviewed image artifacts are hashed. A build with identity drift is rejected rather than being described as the pinned candidate.

`aosp-run-evidence` binds one exact workflow source commit to builder preflight, AOSP plan, resolved-manifest identity, pre-build staging, post-build staged-source verification and hashed build output. It records SHA-256 for every input report and rejects cross-run workspace/revision/manifest/stage/build mixing. When runtime collection is enabled, runtime/smoke/bundle evidence is all-or-nothing and must share the exact build fingerprint and exact source-ready package set. The final report is either `BUILD_ONLY` or `BUILD_AND_RUNTIME`; it never changes registry state automatically.

Cuttlefish runtime evidence still requires `sys.boot_completed=1`, exact product/device/manufacturer identity, Android 17 / API 37, `userdebug`, build ID/fingerprint, every source-ready package and a launcher activity resolving inside each expected package. Emulator-only launch smoke requires successful package-local `am start -W` and resumed-foreground confirmation for every source-ready app. Neither report is physical-device evidence.

No completed source sync, Kati/Soong build or Cuttlefish boot exists yet, so `aosp_baseline` and `emulator_boot` remain incomplete. This iteration removes a real workflow gate defect and strengthens future evidence, but does not itself satisfy a runtime milestone.

### Physical-device observation, install, rollback and recovery evidence

ADB diagnostics capture exact reported firmware fingerprint, board/hardware, slot and verified-boot/VBMeta state while retaining the single-local-USB and fixed-`getprop` allowlist. Fastboot can optionally collect bounded `has-slot:<partition>` and `partition-size:<partition>` hints for reviewed partition names; it still does not use `getvar all` and exposes no reboot/unlock/flash/erase/format/slot-change command.

Saved ADB and Fastboot unified reports can be correlated into integrity-hashed hardware evidence only when both resolve to the same metadata profile, model/codename agree, an exact current firmware fingerprint exists, and reported slot/bootloader state does not conflict. This remains deliberately `CORRELATED_READ_ONLY_NOT_VERIFIED`: it cannot prove that both reports came from the same physical handset, cannot mark a profile supported and always keeps hardware verification, writes, flashing and root false. A preparation transaction may be compared against this evidence and must match profile, codename, model and exact current firmware fingerprint, but even a complete match remains preparation-only.

A preparation-only transaction evidence layer exists before any future device write engine. Schema v1 binds an exact device profile/current-build/target-build tuple to explicit install and rollback artifact sets, verifies their byte sizes and SHA-256 values under an absolute local artifact root, rejects path traversal/symlinks/duplicate JSON keys/unknown fields, and can create a new fsynced recovery journal that is never overwritten.

The layer remains deliberately unable to authorize installation: accepted plans require `write_enabled=false`, explicit owner confirmation remains required but unrecorded, rollback material is mandatory, and journals state `write_allowed=false`. It contains no executable commands or partition/slot instructions. This is useful recovery infrastructure but **does not complete `install_restore`**. The current `avicii` profile still has no verified partition map, firmware baseline, validated SwirPhoneOS build or physical restore evidence.

Before any future write-capable Studio control can exist, correlated observations must be upgraded through controlled physical verification, the journal must be bound to an exact hardware-verified profile and reviewed partition/slot map, owner confirmation must be captured after diagnostics, interrupted-transaction recovery must be deterministic, stock restore must be tested on the same firmware, and update/recovery/SwirRoot coordination must be validated. See `docs/HARDWARE_EVIDENCE.md` and `docs/RECOVERY_TRANSACTIONS.md`.

### Android application source

Ten applications are **`ANDROID_SOURCE`** and included in the Cuttlefish product: SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate, SwirPrivacy, SwirClock, SwirNotes, SwirCalendar and SwirRoot.

SwirRoot is a meaningful Android source-stage control surface rather than a host-only contract. It has an original localized owner UI, a non-exported status/diagnostic service, current-build fingerprint display, a bounded app-private review audit, and a pure-Java enable/unroot gate policy. The checked-in Android service hard-disables its mutation backend and supported-build switch, reports `UNAVAILABLE`, and only reviews safety prerequisites after explicit owner confirmation. No `su`, process-execution, boot-image modification, partition write, unlock, flash or exploit path exists. Source-implemented capabilities are intentionally limited to `root_state` and `authorization_audit`; `guided_enable` and `guided_unroot` remain future capabilities that require an exact physically verified backend plus rollback/recovery evidence.

Source validation scans every production Java file for forbidden execution/network/storage primitives. The SwirRoot contract additionally requires exact-build/profile/owner/rollback/journal/update-state gates and hard-disabled mutation support. All ten apps have eight locale resource sets including Arabic/RTL and dependency-free host tests for reviewed pure-Java logic where applicable.

All ten remain below `ANDROID_RUNTIME`. Source-only work therefore receives no weighted gate credit. Current intentional gaps also include Calculator scientific math, Update staged/recovery state, Privacy live indicators/access history and Calendar provider bridging.

### Desktop and SwirRoot

Read-only ADB/Fastboot/FastbootD diagnostics, multilingual SwirPhoneStudio and Windows developer packaging exist, but real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing. Cross-transport evidence and local transaction evidence give Studio stronger future prerequisites for exact-device/recovery-aware installation, but no write controls are exposed. SwirRoot Android source is present, but there is still no exact-build mutation implementation, supported root build, physical enable/unroot path, recovery proof or per-app privileged authorization backend.

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
2. Preserve `builder-preflight.json`, `aosp-plan.json`, `resolved-manifest.json`, `stage-report.json`, `post-build-stage-evidence.json`, `build-evidence.json`, `runtime-evidence.json`, `app-smoke-evidence.json`, `evidence-bundle.json` and the new `aosp-run-evidence.json`. The final run report must be `BUILD_AND_RUNTIME`, bound to the workflow source commit and exact build fingerprint, before any runtime promotion review.
3. Fix any real Repo/Kati/Soong/Cuttlefish regressions first. Do not weaken pinned build ID/security-patch, staged-source integrity, package-set or fingerprint continuity merely to obtain a green build.
4. Perform focused interactive checks that launch-smoke cannot prove: Settings/Files/Update/Privacy/DeviceCare flows, Notes/Calendar persistence/export, Clock timer/alarm hand-off, SwirRoot's fail-closed state/confirmation/audit UI, accessibility, text expansion, locale switching and Arabic RTL. Only then review any `ANDROID_RUNTIME` promotion.
5. On the owner-controlled `avicii`, capture an ADB `inspect-device` observation while Android is running, then manually enter documented Fastboot/FastbootD and capture the second observation with `--partitions`. Correlate them with `hardware-evidence`, review the exact firmware fingerprint plus reported slot/partition hints, and keep the result explicitly below hardware verification. The profile remains `PLANNED_NOT_SUPPORTED` and no write path should be enabled from correlation alone.
6. Only after the physical observation set is reviewed should a device-specific transaction plan be authored. Bind it with `transaction-device-check`, verify exact target+rollback bytes and create a recovery journal. Physical restore evidence and a verified partition map are still required before any write-capable implementation.
7. Continue SwirPhoneStudio hardening; the next desktop gate evidence is actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device. Later Studio install UI must consume reviewed hardware+transaction evidence rather than inventing recovery state from device hints.
8. After emulator/GSI and recovery evidence, design a legitimate exact-build SwirRoot backend only for explicitly supported unlocked/owner-controlled device paths. Never bypass locked bootloaders, OEM protections or verification controls through exploits.
9. Expand device packs into reviewed installation/recovery plans only after exact-device evidence exists. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
