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

The canonical ledger is [`project.json`](project.json). Host tests, desktop packaging and Android source do not complete build, boot or hardware gates. **Beta: 0/9 gates passed.**

## What works now

### Safety-first host tooling

The `swirphoneos` Python package provides strictly read-only ADB and Fastboot/FastbootD diagnostics. SwirPhoneStudio adds a multilingual dark/blue desktop UI, explicit trusted-tool selection, asynchronous inspection, immutable report export and Windows x64/Python 3.14 developer packaging. No unlock, erase, boot, flash, root, relock or restore control is enabled.

### Android 17 platform foundation

The development baseline is pinned to **Android 17 / API 37** at `android-17.0.0_r1`. The exact identity is recorded in [`platform/aosp_baseline.json`](platform/aosp_baseline.json), but status remains `PINNED_NOT_BUILT`: no completed AOSP sync, Kati/Soong build or Cuttlefish boot is claimed.

The repository contains an x86_64 Cuttlefish product, exact-tag workspace planning, resolved `repo manifest -r` verification, bounded `vendor/swir/` source staging and a strict read-only Cuttlefish evidence collector. Staging now supports independently reviewed `stage_manifest.d/*.json` fragments while enforcing global source/destination uniqueness and the same `vendor/swir/` boundary. Runtime evidence requires the exact product, `sys.boot_completed=1`, a build fingerprint, every source-ready package and a launcher activity resolving inside each expected package. It never launches apps, changes package state or promotes registry status automatically.

### Functional Android application sources

Nine first-party applications are wired into `PRODUCT_PACKAGES` as meaningful **`ANDROID_SOURCE`**. They remain below `ANDROID_RUNTIME` until the pinned AOSP product actually builds and they are exercised in Cuttlefish.

- **SwirCalculator** — host-tested BigDecimal basic arithmetic, locale-aware display and permission-free UI; scientific math remains future work.
- **SwirSettings** — searchable hub with real build/device status and a reviewed allowlist of authoritative Android settings routes.
- **SwirFiles** — user-granted Storage Access Framework tree with browse/search/create/rename/copy/move/delete/open/share; no broad storage permission.
- **SwirDeviceCare** — real framework device/security-patch, battery, storage, memory and thermal diagnostics without privileged permissions.
- **SwirUpdate** — read-only channel/build status plus host-tested SHA-256/RSA metadata verification; download/staging/recovery install remain disabled.
- **SwirPrivacy** — reviewed permission-free routes into Android privacy/permission surfaces; live indicators/access history remain future platform work.
- **SwirClock** — localized local/UTC time, foreground stopwatch/timer and user-visible alarm hand-off without exact-alarm privileges.
- **SwirNotes** — private local SQLite notes with create/edit/delete/search, explicit sharing and user-selected Markdown export; no network or provider permission.
- **SwirCalendar** — local SQLite agenda with date/time editing, search, sharing and portable iCalendar (`.ics`) export; Android CalendarProvider bridging is deliberately not claimed yet.

All nine apps ship English, Polish, Norwegian Bokmål, German, Spanish, French, Portuguese and Arabic resources, including RTL-aware application layout. Their manifests, package identities, permission boundaries, localization parity, host-testable pure-Java policy cores and AOSP staging are checked in CI.

### Complete system-app plan and SwirRoot

The machine-readable suite contains 20 applications: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Current registry state is **9 `ANDROID_SOURCE`, 11 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`**.

SwirRoot remains a fail-closed engineering contract. Unverified builds expose `UNAVAILABLE`; authorization is deny-by-default; rollback material, journaling, exact-build/profile checks and explicit owner confirmation are mandatory; exploit/bypass methods are forbidden; write operations are disabled; supported root builds remain zero.

### Global localization

Host localization is data-driven with system-locale detection and English fallback. The desktop and all nine current Android source apps use EN/PL/NB/DE/ES/FR/PT/AR catalogs. The mobile architecture requires the same localization discipline for first setup, launcher, SystemUI, Settings, recovery, updater, SwirRoot and all bundled apps, including RTL, fonts/scripts, plurals, accessibility and locale-specific formatting.

## Developer commands

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos product-contract
python -m swirphoneos aosp-plan --workspace /path/to/aosp --jobs 16
python -m swirphoneos android-apps
python -m swirphoneos build-preflight --workspace /path/to/aosp
python -m swirphoneos cuttlefish-evidence --adb /absolute/path/to/adb
python -m swirphoneos i18n
python -m swirphoneos apps
python -m swirphoneos root-policy
python -m swirphoneos.studio
```

`gate` intentionally exits blocked while mandatory beta evidence is missing. `android-apps` validates checked-in source only. `cuttlefish-evidence` is read-only emulator evidence and does not by itself prove feature completeness or physical-device compatibility.

## Product direction

**SwirPhoneOS Core:** Linux kernel + AOSP/Android-compatible userspace/HAL integration, shared core where practical, device-specific packs where required, original Swir UI/services/apps, privacy controls and signed OTA updates.

**SwirPhoneStudio:** Windows-first, Linux-capable companion for detection, verified downloads, backup/install planning, transaction journaling, recovery and stock restore. Write controls remain disabled until exact-device safety gates are physically verified.

**SwirRoot:** first-party owner-controlled root enable/disable for explicitly supported SwirPhoneOS builds with verified rollback, diagnostics, per-app authorization and tested unroot/recovery. It does not use bootloader exploits.

**Worldwide use:** every system surface and bundled app uses shared localization architecture, detects the best locale during setup and falls back to English.

## Compatibility and release policy

SwirPhoneOS targets broad Android-device coverage through a shared AOSP/GSI-capable core plus validated device-specific profiles/ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ. Unsupported hardware stays unsupported until evidence exists.

The first planned reference device is OnePlus Nord AC2003 (`avicii`), currently `PLANNED_NOT_SUPPORTED`.

A beta Release requires a reproducible OS build, real boot path, safe install/rollback/recovery, at least one physically verified phone profile, usable core system functionality and verified release artifacts/checksums. Telephony, camera and root capability are stated per tested device/build. **No beta is published now.**

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Build status](BUILD_STATUS.md) · [System Apps](docs/SYSTEM_APPS.md) · [Global i18n](docs/I18N.md) · [AOSP workspace](docs/AOSP_BUILD_WORKSPACE.md) · [Runtime evidence](docs/AOSP_RUNTIME_EVIDENCE.md) · [SwirRoot](docs/SWIRROOT.md) · [Changelog](CHANGELOG.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
