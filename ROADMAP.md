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

The dedicated builder path preserves evidence continuity before the first expensive real run. The workflow consumes the host-preflight `checks[].id` / `checks[].passed` schema, records bounded failure evidence, stages exact source bytes, re-verifies those bytes after Kati/Soong and binds a successful run to the pinned manifest and hashed images. Build evidence requires the exact `swirphoneos_cf_x86_64` identity, Android 17/API 37, build ID `CP2A.260605.016`, security patch `2026-06-05`, `userdebug`, non-empty `boot.img` and `system.img`.

`aosp-run-evidence` binds one workflow source commit to builder preflight, AOSP plan, resolved manifest, pre/post-build staging, build evidence and—when requested—the complete runtime/smoke/bundle group. Runtime still requires `sys.boot_completed=1`, exact product/device/manufacturer identity and every source-ready package with a package-local launcher. Emulator-only smoke requires successful `am start -W` plus resumed-foreground confirmation. None of these reports is physical-device evidence and none auto-promotes app status.

No completed source sync, Kati/Soong build or Cuttlefish boot exists yet, so `aosp_baseline` and `emulator_boot` remain incomplete.

### Physical-device observation, install, rollback and recovery evidence

ADB diagnostics capture exact reported firmware fingerprint, board/hardware, slot and verified-boot/VBMeta state through a strict read-only allowlist. Fastboot can optionally collect bounded `has-slot:<partition>` and `partition-size:<partition>` hints for reviewed partition names; it does not expose `getvar all`, reboot, unlock, flash, erase, format or slot-change operations.

Saved ADB and Fastboot reports can be correlated only when profile/model/codename/build and non-conflicting slot/bootloader hints agree. The result remains deliberately `CORRELATED_READ_ONLY_NOT_VERIFIED`, with hardware verification, support, writes, flashing and root all false. A preparation transaction may be matched against this evidence and must match the exact current firmware fingerprint, but the match remains preparation-only.

The transaction evidence layer binds exact target and rollback artifacts to one profile/current-build/target-build tuple, verifies exact sizes and SHA-256, rejects unsafe paths/symlinks/duplicate keys and can create a new fsynced recovery journal. Journals state `owner_confirmation_recorded=false` and `write_allowed=false`. The current `avicii` profile still has no verified partition map, firmware baseline, SwirPhoneOS build or physical restore evidence.

### Android application source

Twelve applications are **`ANDROID_SOURCE`** and included in the Cuttlefish product: SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate, SwirPrivacy, SwirClock, SwirNotes, SwirCalendar, SwirGallery, SwirRecorder and SwirRoot.

The source validator now uses exact least-privilege permission allowlists rather than assuming every source app must be permission-free. Permission-free applications still fail if they gain any permission. SwirGallery is limited to `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`; SwirRecorder is limited to `RECORD_AUDIO`. Network, broad-storage and process-execution primitives remain globally rejected across production Java source. Every source-ready app has EN/PL/NB/DE/ES/FR/PT/AR resources with key-parity and RTL checks.

SwirGallery provides scoped MediaStore photo/video browsing, local search, open/share and Android owner-confirmed deletion. Album grouping remains an explicit missing target capability. SwirRecorder provides foreground-only AAC/MPEG-4 capture into app-private storage, pause/resume/stop, playback, microphone-mute state, confirmed local deletion and owner-selected document export. Its activity stops any active recording when leaving the foreground; there is no background recording service. Recorder audio behavior remains hardware-dependent and unverified.

SwirRoot remains a source-stage control surface only. Its mutation backend and supported-build switch are hard-disabled, it reports `UNAVAILABLE`, and it contains no `su`, process execution, boot-image mutation, partition write, unlock, flash or exploit path. `guided_enable` and `guided_unroot` remain future capabilities requiring an exact physically verified backend plus rollback/recovery evidence.

All twelve remain below `ANDROID_RUNTIME`. Source-only work therefore receives **no weighted gate credit**. Current intentional gaps also include Calculator scientific math, Gallery albums, Update staged/recovery state, Privacy live indicators/access history and Calendar provider bridging.

### Desktop and SwirRoot

Read-only ADB/Fastboot/FastbootD diagnostics, multilingual SwirPhoneStudio and Windows developer packaging exist, but real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing. Cross-transport evidence and local transaction evidence provide future prerequisites for exact-device/recovery-aware installation, but no write controls are exposed. SwirRoot Android source is present, but there is no exact-build mutation implementation, supported root build, physical enable/unroot path, recovery proof or privileged authorization backend.

## System app delivery track

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the built Android image.
- [ ] Settings, Files, Update, Privacy and Device Care usable with real runtime/platform state.
- [ ] Clock, Calculator, Notes, Calendar, Gallery, Recorder and SwirRoot built and exercised inside SwirPhoneOS Cuttlefish.
- [ ] Runtime permission UX, accessibility, RTL and locale-switch review for all source-ready apps.

> Source progress: twelve apps contain meaningful Android source and host-tested policy/logic, but the checkboxes stay open until they are built and exercised in the SwirPhoneOS image. The global percentage therefore remains 2%.

### Reference-hardware phase

- [ ] Swir Phone/Contacts/Messages validated against the exact reference telephony stack.
- [ ] Swir Camera validated against the exact reference camera/media stack.
- [ ] Swir Gallery scoped MediaStore behavior validated on the supported build and expanded with reviewed album behavior.
- [ ] Swir Recorder capture/playback/export validated against the reference microphone/audio stack.
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

1. Provision or attach a capable dedicated Linux x86-64 runner labeled `swir-aosp-builder`, set `SWIR_AOSP_WORKSPACE`, ensure Cuttlefish host prerequisites plus the trusted absolute `adb` path exist, and run the manual `AOSP build evidence` workflow with runtime collection enabled. It must initialize/sync exact `android-17.0.0_r1`, preserve `repo manifest -r`, stage the bounded `vendor/swir/` bundle and compile `swirphoneos_cf_x86_64-aosp_current-userdebug` with all twelve source-ready apps.
2. Preserve `builder-preflight.json`, `aosp-plan.json`, `resolved-manifest.json`, `stage-report.json`, `post-build-stage-evidence.json`, `build-evidence.json`, `runtime-evidence.json`, `app-smoke-evidence.json`, `evidence-bundle.json` and `aosp-run-evidence.json`. The final run report must be `BUILD_AND_RUNTIME`, bound to the workflow source commit and exact build fingerprint, before any runtime promotion review.
3. Fix any real Repo/Kati/Soong/AAPT/Cuttlefish regressions first. Do not weaken pinned build identity, staged-source integrity, exact permission allowlists, package-set or fingerprint continuity merely to obtain a green build.
4. Perform focused interactive checks launch-smoke cannot prove: Settings/Files/Update/Privacy/DeviceCare flows; Notes/Calendar persistence/export; Clock timer/alarm hand-off; Gallery permission/search/open/share/delete behavior; Recorder runtime permission, capture/pause/resume/stop/playback/export and foreground-stop behavior; SwirRoot's fail-closed UI; accessibility, text expansion, locale switching and Arabic RTL. Only then review any `ANDROID_RUNTIME` promotion.
5. On the owner-controlled `avicii`, capture read-only ADB and Fastboot/FastbootD observations and correlate them with `hardware-evidence`. Review the exact firmware fingerprint, slots and bounded partition hints while keeping the result below hardware verification and the profile `PLANNED_NOT_SUPPORTED`.
6. Only after physical observations are reviewed should a device-specific transaction plan be authored. Bind it with `transaction-device-check`, verify target+rollback bytes and create a recovery journal. Physical restore evidence and a verified partition map remain mandatory before any write-capable implementation.
7. Continue SwirPhoneStudio hardening; the next desktop gate evidence is actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device. Later install UI must consume reviewed hardware+transaction evidence rather than infer recovery state from hints.
8. After emulator/GSI and recovery evidence, design a legitimate exact-build SwirRoot backend only for explicitly supported unlocked/owner-controlled device paths. Never bypass locked bootloaders, OEM protections or verification controls through exploits.
9. Expand device packs into reviewed installation/recovery plans only after exact-device evidence exists. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
