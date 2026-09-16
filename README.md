<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, Windows EXE, installer, backup or stock-restore implementation is available yet. Runnable components are read-only Python host diagnostics and the Flash Studio desktop GUI source.

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

Each bar segment represents a completed 5 percentage points, rounded down. [project.json](project.json) is the machine-readable ledger; [ROADMAP.md](ROADMAP.md) defines weights and evidence. The completed foundation gate is worth only 2 points. Desktop/unit/CI tests do not complete system or hardware gates. **Beta: 0/9 gates passed.**

## What works now

The `swirphoneos` Python package provides selected read-only **ADB** property inspection and a separate strictly read-only **Fastboot/FastbootD** inspection path. Both require explicit trusted Android SDK executable paths, enforce single-device handling and keep raw transport errors private. Fastboot queries only `product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace` and `secure`, rechecks device identity, distinguishes reported bootloader Fastboot from FastbootD, and rejects every command outside that tiny read-only allowlist. Reports always keep `flash_allowed: false` and never make a support claim.

A strict **device profile registry** validates metadata in `device_packs/<vendor>/<codename>/profile.json`. Schema v1 is deliberately non-executable: it rejects `flash_enabled: true`, rejects flash operations, requires safe `vendor/codename` IDs, validates bounded model allowlists and HTTPS sources, and rejects duplicate profile IDs. The existing OnePlus Nord AC2003 (`avicii`) entry remains `PLANNED_NOT_SUPPORTED`; metadata is not a working port.

**Flash Studio has a runnable desktop window:** dark/blue branding and the custom icon, trusted ADB file selection, background read-only inspection, elapsed status, read-only JSON report display, create-only local export and a `by Swir` GitHub footer. English, Polish and Norwegian Bokmal catalogs use the system UI language with English fallback; the language can also be changed in the window. Failed inspections clear stale reports. No installation button or write operation is exposed. Fastboot/profile integration into the GUI remains a later desktop step; the new Fastboot/profile paths are currently available through the core/CLI.

The platform layer records an **Android 17 / API 37 AOSP baseline candidate**. At the 2026-09-16 upstream check, AOSP's recommended `android-latest-release` manifest resolved to `android17-release`; the candidate record references `android-17.0.0_r1` / `CP2A.260605.016`. Its status is deliberately `CANDIDATE_NOT_PINNED`: no source sync or Android build is claimed. See [AOSP baseline policy](docs/UPSTREAM_BASELINE.md).

The status command validates the weighted roadmap and mandatory beta gate ledger. Publication remains disabled even if someone manually checks every ledger box: an independent candidate/artifact/evidence verifier is still required.

The merged desktop slice recorded **46 new local tests** on Linux/Python 3.13.5, including **7 real Tk-window tests with synthetic inspection**, plus the prior 41 foundation host tests. Windows/Linux Python 3.11–3.14 CI runs native Tk smoke checks. New Fastboot/profile/platform code adds portable host-side tests and CI metadata validation. No physical phone has been validated. A green host matrix still does not establish phone compatibility. See [BUILD_STATUS.md](BUILD_STATUS.md).

## Try the developer tools

Run from the repository root with Python 3.11 or newer. No third-party Python packages are needed; the GUI requires Tk and a graphical desktop.

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos.studio
```

`profiles` validates and lists the metadata-only device registry. `baseline` validates and prints the offline AOSP candidate metadata without downloading source. Neither authorizes flashing. `gate` deliberately exits with code **2** while publication is blocked; this is expected, not a failed host test. Errors exit with code 1. See [Flash Studio instructions](docs/FLASH_STUDIO.md) for native GUI testing, export behavior and current limitations.

### Read-only ADB inspection

Optional ADB inspection requires your own trusted Android SDK Platform Tools, an authorized USB-debugging connection and exactly one USB phone. Supply an absolute executable path; the tool does not search PATH, download binaries or install drivers.

```powershell
python -m swirphoneos inspect --adb "C:\Android\platform-tools\adb.exe"
```

```sh
python -m swirphoneos inspect --adb /opt/android/platform-tools/adb
```

### Read-only Fastboot / FastbootD inspection

With exactly one phone already placed in Fastboot or FastbootD mode, supply the trusted Android SDK `fastboot` binary explicitly:

```powershell
python -m swirphoneos inspect-fastboot --fastboot "C:\Android\platform-tools\fastboot.exe"
```

```sh
python -m swirphoneos inspect-fastboot --fastboot /opt/android/platform-tools/fastboot
```

The Fastboot diagnostic command does **not** reboot the phone, unlock the bootloader, erase data, change slots, boot an image, flash, format, relock or restore anything. Unsupported variables remain unknown rather than becoming proof of compatibility.

Manufacturer/model/bootloader/Treble/Fastboot values are device-reported hints, not trusted hardware identity or proof of GSI compatibility. Missing information stays unknown. No serial/IMEI property is intentionally requested. Device-reported values must still be reviewed before sharing a report publicly; nothing uploads automatically.

## Product direction

**SwirPhoneOS Core:** maintainable AOSP/Linux integration beginning from a reproducibly pinned Android 17 candidate after build-host preflight; ARM64 GSI where compatible; device-specific ports where necessary; custom launcher/SystemUI/settings; polished dark/neon visual design; privacy controls; and signed OTA updates. Android app compatibility is a goal; Google services and individual apps are not guaranteed.

**First-party system apps:** SwirPhoneOS is planned as a complete everyday phone OS, not only a bootable image. The canonical suite includes Swir Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. All apps share one original SwirPhoneOS design system, icon family, localization/accessibility rules and system-level integration. See [System Apps](docs/SYSTEM_APPS.md).

**SwirRoot:** a first-party owner-controlled root manager for explicitly supported SwirPhoneOS builds/device profiles. The design requires clear root state, verified rollback material, explicit confirmation, diagnostics, a tested unroot path and integration with Swir Update/recovery/SwirPhoneStudio. It must not bypass locked bootloaders or OEM protections with exploits, and it is not counted as working until enable/disable/recovery behavior is physically verified.

**SwirPhoneOS Flash Studio / SwirPhoneStudio:** a Windows-first, Linux-capable desktop companion. The first read-only GUI slice is implemented. The host core now also contains strict Fastboot/FastbootD diagnostics and a non-executable device registry. Planned next capabilities include GUI integration of those diagnostics, verified downloads, bounded pre-flight checks, packaged Windows delivery, user-confirmed installation plans, a transaction journal and tested per-device recovery before any write controls are enabled.

**First planned reference:** OnePlus Nord AC2003 (`avicii`). Its profile is explicitly `PLANNED_NOT_SUPPORTED`, with no firmware baseline, validated partition map or flash operations. Metadata is not a working port.

## Compatibility strategy

SwirPhoneOS is designed around a shared AOSP/GSI-capable core plus explicit device packs and, where required, device-specific ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ.

The long-term goal is therefore **broad Android-device coverage through automatic detection and validated profiles**, not pretending that unknown hardware is safe to flash. Devices with permanently locked bootloaders or unavailable vendor/kernel support may remain unsupported.

## Safety and release policy

There is no universal installer for every Android phone. Treble support alone is insufficient. Unlocking a bootloader can erase user data; full backups and stock restoration cannot be promised for every device. No unattended physical-device modification is authorized by this project automation. See [SECURITY.md](SECURITY.md) and [upstream sources](docs/SOURCES.md).

A beta Release must contain a usable tested system image and verified Windows companion, not a renamed source ZIP. [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) requires exact-build hardware, install/recovery, security and artifact evidence. No beta is published now.

## Development

This repository is the sole source of truth for the mobile project previously called SwirOS foundation v0.0.1. It is separate from SWIR OS Desktop, Konofix and KaliPhoneStudio. Repository-facing content is English, with localized runtime translation catalogs; progress reports to the owner are Polish. Scheduled development must follow [AGENTS.md](AGENTS.md), not inflate completion or claim unattended continuous computation.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [System Apps](docs/SYSTEM_APPS.md) · [Changelog](CHANGELOG.md) · [AOSP baseline](docs/UPSTREAM_BASELINE.md) · [Licensing policy](LICENSES.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
