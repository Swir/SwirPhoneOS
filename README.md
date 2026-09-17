<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, installer, backup or stock-restore implementation is available yet. Meaningful Android application source exists, but no APK/runtime claim is made before a real pinned-AOSP build and boot.

<!-- SWIR-ROADMAP-STANDARD:v1 -->
![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Roadmap](https://img.shields.io/badge/ROADMAP-2%25-blue)
![Done](https://img.shields.io/badge/DONE-1%2F10_milestones-blue)
![Status](https://img.shields.io/badge/STATUS-foundation-orange)

## Overall progress

**2% — weighted engineering milestones, not phone compatibility.**

`[--------------------] 2%`

| Completed milestones | Remaining | Total | Weighted progress |
| --- | --- | --- | --- |
| 1 | 9 | 10 | 2% |

The canonical ledger is [`project.json`](project.json). Host tests, desktop packaging, Android source, read-only hardware correlation and local transaction preparation do not complete build, boot or hardware gates. **Beta: 0/9 gates passed.**

## What works now

### Safety-first host tooling

The `swirphoneos` Python package provides strictly read-only ADB and Fastboot/FastbootD diagnostics. SwirPhoneStudio adds a multilingual dark/blue desktop UI, explicit trusted-tool selection, asynchronous inspection, immutable report export and Windows x64/Python 3.14 developer packaging. No unlock, erase, boot, flash, root, relock or restore control is enabled.

Physical-device evidence gathering records exact firmware/build fingerprint, board/hardware, slot and verified-boot/VBMeta hints through a narrow ADB allowlist. Fastboot can optionally record bounded `has-slot` and `partition-size` hints for reviewed partition names without `getvar all`. Saved ADB and Fastboot observations can be correlated only when profile/model/codename/build and non-conflicting slot/bootloader hints agree. The integrity-hashed result remains explicitly `CORRELATED_READ_ONLY_NOT_VERIFIED`: it cannot claim support, verify hardware or enable writes, flashing, root or restore.

A local-only transaction evidence layer prepares the recovery side of future installation work without contacting a phone. Schema v1 binds one exact profile/current-build/target-build tuple to explicit target and rollback files, verifies each file's size and SHA-256 under a confined local root, rejects traversal/symlinks/duplicate keys/unknown fields, and can persist a create-only fsynced recovery journal. Accepted plans require rollback and explicit owner confirmation, but the journal deliberately records `owner_confirmation_recorded=false` and `write_allowed=false`. None of this makes the current `avicii` profile supported or completes the install/restore milestone.

### Android 17 platform foundation

The development baseline is pinned to **Android 17 / API 37** at `android-17.0.0_r1`. The exact identity is recorded in [`platform/aosp_baseline.json`](platform/aosp_baseline.json), but status remains `PINNED_NOT_BUILT`: no completed AOSP sync, Kati/Soong build or Cuttlefish boot is claimed.

The repository contains an x86_64 Cuttlefish product, exact-tag workspace planning, resolved `repo manifest -r` verification, bounded `vendor/swir/` source staging and strict build/runtime evidence tooling. Schema-v5 staging requires exact destination-tree closure before and after compilation so a persistent build host cannot silently compile stale or unreviewed Swir files. `build-evidence` requires hashed core images and the exact pinned Android release/API, build ID `CP2A.260605.016`, security patch `2026-06-05` and `userdebug` type from the built product.

The manual-only self-hosted `aosp-build-evidence.yml` workflow binds the exact workflow source commit to builder preflight, exact AOSP plan, resolved manifest, staging before build, post-build staged-source evidence and build evidence. When runtime collection is explicitly enabled it can launch the **exact product it just built**, wait for strict boot evidence, run emulator-only launch smoke over every source-ready app, bind build/runtime fingerprints and clean up Cuttlefish. Failed runs retain only bounded diagnostic evidence. This path is implemented but has **not** completed a real AOSP build/boot yet.

### Functional Android application sources

Sixteen first-party applications are wired into `PRODUCT_PACKAGES` as meaningful **`ANDROID_SOURCE`**. They remain below `ANDROID_RUNTIME` until the pinned AOSP product actually builds and they are exercised in Cuttlefish.

- **Swir Phone** — permission-free keypad with host-tested fail-closed dial-string normalization and an explicit `ACTION_DIAL` hand-off to Android's system dialer. It never places calls silently; default-dialer role, in-call UI and recent-call history remain future exact-telephony work.
- **Swir Messages** — permission-free local composer with app-private draft persistence, host-tested recipient/body bounds and an explicit `ACTION_SENDTO`/`smsto:` hand-off to an installed Android messaging app. It never silently sends or reads SMS; MMS, conversation history, default-SMS role and carrier delivery remain future exact-telephony work.
- **SwirCalculator** — host-tested BigDecimal basic arithmetic and locale-aware display; scientific math remains future work.
- **SwirSettings** — searchable hub with real build/device status and a reviewed allowlist of authoritative Android settings routes.
- **SwirFiles** — user-granted Storage Access Framework tree with browse/search/create/rename/copy/move/delete/open/share and no broad storage permission.
- **SwirDeviceCare** — framework-backed device/security-patch, battery, storage, memory and thermal diagnostics without privileged permissions.
- **SwirUpdate** — read-only channel/build status plus host-tested SHA-256/RSA metadata verification; download/staging/recovery install remain disabled.
- **SwirPrivacy** — reviewed permission-free routes into Android privacy/permission surfaces; live indicators/access history remain future platform work.
- **SwirClock** — localized time, foreground stopwatch/timer and user-visible alarm hand-off without exact-alarm privileges.
- **SwirNotes** — private local SQLite notes with create/edit/delete/search, explicit sharing and user-selected Markdown export.
- **SwirCalendar** — local SQLite agenda with editing/search/share and iCalendar export; CalendarProvider bridging remains future work.
- **SwirGallery** — scoped photo/video MediaStore browser with search/open/share and Android owner-confirmed deletion; albums remain future work.
- **SwirRecorder** — foreground-only private AAC/MPEG-4 recording with pause/resume/stop/playback, microphone state and explicit document export; exact-device audio behavior is unverified.
- **SwirContacts** — local ContactsProvider browse/search using exactly `READ_CONTACTS`, Android-managed create/edit, explicit vCard import hand-off and user-selected vCard export. It does not request `WRITE_CONTACTS` or network access.
- **Swir Apps** — permission-free local Software Center catalog for launchable apps with package/version and signing-certificate SHA-256 provenance, app launch and authoritative Android app-details hand-off. Remote catalog/install/update status is deliberately not implemented.
- **SwirRoot** — original owner-facing root-state/safety UI plus a non-exported status/diagnostic service and host-tested transition policy. It remains `UNAVAILABLE`; mutation support and supported-build switches are hard-disabled.

All sixteen apps ship English, Polish, Norwegian Bokmål, German, Spanish, French, Portuguese and Arabic resources with RTL-aware application layout. Source validation checks package identity, exact per-app permission allowlists, localization parity, pure-Java policy cores and complete bounded AOSP staging. It scans every production Java file for forbidden process/network/broad-storage primitives; SwirRoot receives additional fail-closed checks. Contacts is limited to `READ_CONTACTS`, Gallery to `READ_MEDIA_IMAGES` + `READ_MEDIA_VIDEO`, Recorder to `RECORD_AUDIO`, and all other current source apps — including Swir Phone and Swir Messages — remain permission-free. Android localization lint additionally verifies exact source-key coverage, formatter/plural contracts and common hardcoded Java UI sinks; this remains source-only evidence, not runtime RTL proof.

Source-summary schema v3 also tracks unfinished capabilities **per application**. This prevents one app implementing a shared capability name from hiding another app's gap; for example, SwirContacts implements its provider bridge while `calendar:provider_bridge` remains explicitly unfinished, `apps:update_status` remains unfinished, Swir Phone keeps `phone:in_call` plus `phone:recent_calls` open, and Swir Messages keeps `messages:mms` plus `messages:conversation_history` open.

The `swirphoneos.cuttlefish_smoke` runner is deliberately emulator-only. It first requires complete exact-identity Cuttlefish evidence, then launches each already-installed source-ready package through its resolved package-local launcher component, requires Android `am start -W` success and confirms the expected package as resumed foreground activity. It never promotes app status automatically.

### Complete system-app plan and SwirRoot

The machine-readable suite contains 20 applications: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Current registry state is **16 `ANDROID_SOURCE`, 4 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`**.

SwirRoot has meaningful Android source for its owner-facing state, diagnostics, audit and safety-review surface, but it is **not a working root implementation**. Unverified builds remain `UNAVAILABLE`; authorization is deny-by-default; rollback material, journaling, exact-build/profile checks and explicit owner confirmation remain mandatory; exploit/bypass methods are forbidden; Android mutation support is hard-disabled; supported root builds remain zero. `guided_enable` and `guided_unroot` remain target capabilities until a legitimate exact-build backend and tested rollback/unroot path exist.

### Global localization

Host localization is data-driven with system-locale detection and English fallback. The desktop and all sixteen current Android source apps use EN/PL/NB/DE/ES/FR/PT/AR catalogs. The mobile architecture requires the same localization discipline for first setup, launcher, SystemUI, Settings, recovery, updater, SwirRoot and all bundled apps, including RTL, fonts/scripts, plurals, accessibility and locale-specific formatting.

## Developer commands

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos product-contract
python -m swirphoneos aosp-plan --workspace /path/to/aosp --jobs 16
python -m swirphoneos aosp-manifest --file /path/to/aosp/swirphoneos-pinned-manifest.xml
python -m swirphoneos android-apps
python -m swirphoneos build-preflight --workspace /path/to/aosp
python -m swirphoneos build-evidence --workspace /path/to/aosp --manifest /path/to/aosp/swirphoneos-pinned-manifest.xml
python -m swirphoneos cuttlefish-evidence --adb /absolute/path/to/adb > runtime-evidence.json
python -m swirphoneos.cuttlefish_smoke --adb /absolute/path/to/adb > app-smoke-evidence.json
python -m swirphoneos evidence-bundle --build build-evidence.json --runtime runtime-evidence.json
python -m swirphoneos aosp-run-evidence --source-commit <40-char-sha> --preflight builder-preflight.json --plan aosp-plan.json --manifest resolved-manifest.json --stage stage-report.json --post-stage post-build-stage-evidence.json --build build-evidence.json --runtime runtime-evidence.json --smoke app-smoke-evidence.json --bundle evidence-bundle.json
python -m swirphoneos inspect-device --transport adb --tool /absolute/path/to/adb > adb-observation.json
python -m swirphoneos inspect-device --transport fastboot --tool /absolute/path/to/fastboot --partitions > fastboot-observation.json
python -m swirphoneos hardware-evidence --adb-report adb-observation.json --fastboot-report fastboot-observation.json > hardware-evidence.json
python -m swirphoneos transaction-plan --file /absolute/path/to/plan.json
python -m swirphoneos transaction-device-check --plan /absolute/path/to/plan.json --hardware /absolute/path/to/hardware-evidence.json
python -m swirphoneos transaction-evidence --plan /absolute/path/to/plan.json --artifacts /absolute/path/to/artifacts
python -m swirphoneos i18n
python -m swirphoneos apps
python -m swirphoneos root-policy
python -m swirphoneos.studio
```

`gate` intentionally exits blocked while mandatory beta evidence is missing. `android-apps` validates checked-in source only. Hardware correlation and transaction matching are read-only evidence/preparation surfaces and cannot authorize phone writes. Build/run/runtime/app-smoke evidence remains emulator/build evidence, not physical-device compatibility proof.

## Product direction

**SwirPhoneOS Core:** Linux kernel + AOSP/Android-compatible userspace/HAL integration, shared core where practical, device-specific packs where required, original Swir UI/services/apps, privacy controls and signed OTA updates.

**SwirPhoneStudio:** Windows-first, Linux-capable companion for detection, verified downloads, backup/install planning, transaction journaling, recovery and stock restore. Write controls remain disabled until exact-device safety gates are physically verified.

**SwirRoot:** first-party owner-controlled root enable/disable for explicitly supported SwirPhoneOS builds with verified rollback, diagnostics, per-app authorization and tested unroot/recovery. It does not use bootloader exploits or protection bypasses. Current Android source deliberately stops before mutation execution.

**Worldwide use:** every system surface and bundled app uses shared localization architecture, detects the best locale during setup and falls back to English.

## Compatibility and release policy

SwirPhoneOS targets broad Android-device coverage through a shared AOSP/GSI-capable core plus validated device-specific profiles/ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ. Unsupported hardware stays unsupported until evidence exists.

The first planned reference device is OnePlus Nord AC2003 (`avicii`), currently `PLANNED_NOT_SUPPORTED`.

A beta Release requires a reproducible OS build, real boot path, safe install/rollback/recovery, at least one physically verified phone profile, usable core system functionality and verified release artifacts/checksums. Telephony, camera, recorder/audio and SwirRoot are stated per exact tested device/build. **No beta is published now.**

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Build status](BUILD_STATUS.md) · [System Apps](docs/SYSTEM_APPS.md) · [Global i18n](docs/I18N.md) · [AOSP workspace](docs/AOSP_BUILD_WORKSPACE.md) · [AOSP builder evidence](docs/AOSP_BUILDER_EVIDENCE.md) · [Runtime evidence](docs/AOSP_RUNTIME_EVIDENCE.md) · [Hardware evidence](docs/HARDWARE_EVIDENCE.md) · [Recovery transactions](docs/RECOVERY_TRANSACTIONS.md) · [SwirRoot](docs/SWIRROOT.md) · [Changelog](CHANGELOG.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
