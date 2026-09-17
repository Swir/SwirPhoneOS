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

Android 17 / API 37 is pinned to `android-17.0.0_r1`. Exact-tag planning, build-host preflight, resolved-manifest SHA validation and bounded AOSP staging exist. Schema-v5 staging requires the exact reviewed regular-file set under `vendor/swir/` both before and after compilation, rejecting stale files, generated extras, symlinks and hard-link aliases rather than silently cleaning a persistent builder workspace.

The dedicated builder workflow records bounded failure evidence and binds successful runs to exact preflight, AOSP plan, resolved manifest, staged source, build identity and optional runtime. Build evidence requires the exact `swirphoneos_cf_x86_64` identity, Android 17/API 37, build ID `CP2A.260605.016`, security patch `2026-06-05`, `userdebug`, non-empty `boot.img` and `system.img`.

`aosp-run-evidence` binds one workflow source commit to builder preflight, AOSP plan, resolved manifest, pre/post-build staging, build evidence and—when requested—the complete runtime/smoke/bundle group. Runtime still requires `sys.boot_completed=1`, exact product/device/manufacturer identity and every source-ready package with a package-local launcher. Emulator-only smoke requires successful `am start -W` plus resumed-foreground confirmation. None of these reports is physical-device evidence and none auto-promotes app status.

No completed source sync, Kati/Soong build or Cuttlefish boot exists yet, so `aosp_baseline` and `emulator_boot` remain incomplete.

### Physical-device observation, install, rollback and recovery evidence

ADB diagnostics capture exact reported firmware fingerprint, board/hardware, slot and verified-boot/VBMeta state hints through a strict read-only allowlist. Fastboot can optionally collect bounded `has-slot:<partition>` and `partition-size:<partition>` hints for reviewed partition names; it does not expose `getvar all`, reboot, unlock, flash, erase, format or slot-change operations.

Saved ADB and Fastboot reports can be correlated only when profile/model/codename/build and non-conflicting slot/bootloader hints agree. The result remains `CORRELATED_READ_ONLY_NOT_VERIFIED`, with hardware verification, support, writes, flashing and root all false. The current `avicii` profile still has no verified partition map, firmware baseline, SwirPhoneOS build or physical restore evidence.

The transaction evidence layer binds exact target and rollback artifacts to one profile/current-build/target-build tuple, verifies exact sizes and SHA-256, rejects unsafe paths/symlinks/duplicate keys and can create a new fsynced recovery journal. Journals state `owner_confirmation_recorded=false` and `write_allowed=false`.

### Android application source

Sixteen applications are **`ANDROID_SOURCE`** and included in the Cuttlefish product: Swir Phone, Swir Messages, SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate, SwirPrivacy, SwirClock, SwirNotes, SwirCalendar, SwirGallery, SwirRecorder, SwirContacts, Swir Apps and SwirRoot.

The source validator uses exact least-privilege permission allowlists. Permission-free applications fail if they gain any permission. SwirContacts is limited to `READ_CONTACTS`, SwirGallery to `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`, and SwirRecorder to `RECORD_AUDIO`; Swir Phone and Swir Messages remain permission-free. Phone hands a validated number to Android using `ACTION_DIAL`, while Messages hands a bounded recipient/body draft to Android using `ACTION_SENDTO` + `smsto:` rather than silently placing calls or sending SMS. Network, broad-storage and process-execution primitives remain globally rejected across production Java source. Every source-ready app has EN/PL/NB/DE/ES/FR/PT/AR resources with key/formatter/plural validation and RTL-aware application configuration.

Swir Phone provides a real owner-visible keypad, fail-closed dial-string normalization and explicit system-dialer hand-off. It does not request `CALL_PHONE`, does not read call history, and does not claim default-dialer, in-call or recent-call behavior; `phone:in_call` and `phone:recent_calls` remain explicit gaps until the exact Android Telecom/telephony stack and reference hardware are exercised.

Swir Messages provides a real local compose surface, app-private draft persistence, fail-closed recipient/body bounds and an explicit system-messaging hand-off. It does not request `SEND_SMS`, `READ_SMS` or `RECEIVE_SMS`, does not call `SmsManager`, and does not claim default-SMS role, carrier delivery, MMS or provider-backed history. `messages:mms` and `messages:conversation_history` remain explicit gaps until the exact Android telephony/provider stack and reference hardware are exercised.

SwirContacts provides real provider-backed browse/search, delegates contact creation/editing to Android's authoritative contact UI, and supports explicit user-selected vCard import/export flows without requesting `WRITE_CONTACTS`. Swir Apps provides a permission-free local launcher catalog with package/version state and signing-certificate SHA-256 provenance plus launch and app-details navigation. It deliberately has no network installer or remote update catalog yet.

Source-summary schema v3 tracks missing capabilities by app, not only by capability name. This prevents a shared label from obscuring unfinished work: Contacts can truthfully implement its `provider_bridge` while `calendar:provider_bridge` stays open; `apps:update_status`, `messages:mms` and `messages:conversation_history` also stay open.

SwirRoot remains a source-stage control surface only. Its mutation backend and supported-build switch are hard-disabled, it reports `UNAVAILABLE`, and it contains no `su`, process execution, boot-image mutation, partition write, unlock, flash or exploit path. `guided_enable` and `guided_unroot` remain future capabilities requiring an exact physically verified backend plus rollback/recovery evidence.

All sixteen remain below `ANDROID_RUNTIME`. Source-only work therefore receives **no weighted gate credit**. Current intentional gaps include Phone in-call/recent-call integration, Messages MMS/conversation-history/default-role integration, Calculator scientific math, Gallery albums, Update staged/recovery state, Privacy live indicators/access history, Calendar provider bridging, Swir Apps remote update status and SwirRoot guided enable/unroot.

### Desktop and SwirRoot

Read-only ADB/Fastboot/FastbootD diagnostics, multilingual SwirPhoneStudio and Windows developer packaging exist, but real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing. Cross-transport evidence and local transaction evidence provide future prerequisites for exact-device/recovery-aware installation, but no write controls are exposed. SwirRoot Android source is present, but there is no exact-build mutation implementation, supported root build, physical enable/unroot path, recovery proof or privileged authorization backend.

## System app delivery track

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the built Android image.
- [ ] Settings, Files, Update, Privacy and Device Care usable with real runtime/platform state.
- [ ] Phone keypad/handoff, Messages compose/handoff, Clock, Calculator, Notes, Calendar, Gallery, Recorder, Contacts, Swir Apps and SwirRoot built and exercised inside SwirPhoneOS Cuttlefish.
- [ ] Runtime permission UX, accessibility, RTL and locale-switch review for all source-ready apps.

> Source progress: sixteen apps contain meaningful Android source and host-tested policy/logic, but the checkboxes stay open until they are built and exercised in the SwirPhoneOS image. The global percentage therefore remains 2%.

### Reference-hardware phase

- [ ] Swir Phone in-call/default-dialer/recent-call behavior and Swir Messages default-role/provider/MMS/carrier behavior validated against the exact reference telephony stack; Contacts runtime/provider behavior validated on that same build.
- [ ] Swir Camera validated against the exact reference camera/media stack.
- [ ] Swir Gallery scoped MediaStore behavior validated on the supported build and expanded with reviewed album behavior.
- [ ] Swir Recorder capture/playback/export validated against the reference microphone/audio stack.
- [ ] Swir Backup/restore aligned with exact encryption/storage/recovery behavior.
- [ ] Calendar provider bridge, Browser, Weather and Swir Apps update integration brought to beta-appropriate quality.

### SwirRoot phase

- [x] Source-ready permission-free owner UI/service foundation with `UNAVAILABLE` default, explicit confirmation and fail-closed policy review.
- [ ] Authoritative ROOT OFF / ROOT ON / UNAVAILABLE state for an exact physically verified build/profile.
- [ ] Enable-root requires exact supported build/profile, owner confirmation, verified rollback material, durable transaction journaling and safe update state.
- [ ] Unroot restores the expected non-root boot/system state on the exact build/profile.
- [ ] Per-app root authorization is deny-by-default, revocable and auditable through a real privileged backend.
- [ ] SwirRoot integrates with Swir Update, recovery and SwirPhoneStudio.
- [ ] Physical enable → reboot → use → disable → recovery validation before any beta root claim.

## Next engineering work

1. Provision or attach a capable dedicated Linux x86-64 runner labeled `swir-aosp-builder`, set `SWIR_AOSP_WORKSPACE`, ensure Cuttlefish host prerequisites plus the trusted absolute `adb` path exist, and run the manual `AOSP build evidence` workflow with runtime collection enabled. It must initialize/sync exact `android-17.0.0_r1`, preserve `repo manifest -r`, stage the bounded `vendor/swir/` bundle and compile `swirphoneos_cf_x86_64-aosp_current-userdebug` with all sixteen source-ready apps.
2. Preserve `builder-preflight.json`, `aosp-plan.json`, `resolved-manifest.json`, `stage-report.json`, `post-build-stage-evidence.json`, `build-evidence.json`, `runtime-evidence.json`, `app-smoke-evidence.json`, `evidence-bundle.json` and `aosp-run-evidence.json`. The final run report must be `BUILD_AND_RUNTIME`, bound to the workflow source commit and exact build fingerprint, before any runtime promotion review.
3. Fix any real Repo/Kati/Soong/AAPT/Cuttlefish regressions first. Do not weaken pinned build identity, staged-source integrity, exact permission allowlists, package-set or fingerprint continuity merely to obtain a green build.
4. Perform focused interactive checks launch-smoke cannot prove: core Settings/Files/Update/Privacy/DeviceCare flows; Swir Phone keypad normalization and owner-visible `ACTION_DIAL` hand-off; Swir Messages draft persistence, recipient normalization and owner-visible `ACTION_SENDTO` hand-off; Notes/Calendar persistence/export; Clock timer/alarm hand-off; Gallery permission/search/open/share/delete; Recorder runtime permission/capture/playback/export; Contacts permission/search/create/edit/import/export; Swir Apps search/provenance/launch/details; SwirRoot's fail-closed UI; accessibility, text expansion, locale switching and Arabic RTL. Only then review any `ANDROID_RUNTIME` promotion.
5. On the owner-controlled `avicii`, capture read-only ADB and Fastboot/FastbootD observations and correlate them with `hardware-evidence`. Review the exact firmware fingerprint, slots and bounded partition hints while keeping the result below hardware verification and the profile `PLANNED_NOT_SUPPORTED`.
6. Only after physical observations are reviewed should a device-specific transaction plan be authored. Bind it with `transaction-device-check`, verify target+rollback bytes and create a recovery journal. Physical restore evidence and a verified partition map remain mandatory before any write-capable implementation.
7. Continue SwirPhoneStudio hardening; the next desktop gate evidence is actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device.
8. After emulator/GSI and recovery evidence, design a legitimate exact-build SwirRoot backend only for explicitly supported unlocked/owner-controlled device paths. Never bypass locked bootloaders, OEM protections or verification controls through exploits.
9. Expand device packs into reviewed installation/recovery plans only after exact-device evidence exists. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
