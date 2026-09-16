<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, Windows EXE, installer, backup or stock-restore implementation is available yet. Runnable components are a read-only Python diagnostic CLI and the Flash Studio desktop GUI source.

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

Each bar segment represents a completed 5 percentage points, rounded down. [project.json](project.json) is the machine-readable ledger; [ROADMAP.md](ROADMAP.md) defines weights and evidence. The completed foundation gate is worth only 2 points. Desktop unit tests do not complete system or hardware gates. **Beta: 0/9 gates passed.**

## What works now

The `swirphoneos` Python package provides selected read-only ADB property inspection, strict single-device selection, private error messages, a command allowlist, unknown-state handling and a second device-identity check. Reports never authorize flashing. The status command validates the weighted roadmap and mandatory beta gate ledger. Publication remains disabled even if someone manually checks every ledger box: an independent candidate/artifact/evidence verifier is still required.

**Flash Studio now has a runnable desktop window:** dark/blue branding and the custom icon, a trusted ADB file picker, background read-only inspection, elapsed status, read-only JSON report display, create-only local export and a `by Swir` GitHub footer. English, Polish and Norwegian Bokmal catalogs use the system UI language with English fallback; the language can also be changed in the window. Failed inspections clear stale reports. No installation button or write operation is exposed.

Local Linux/Python 3.13.5 verification for the desktop addition: **46 new tests passed**, including **7 real Tk-window tests with synthetic inspection**, plus compile and GUI entry-point smoke checks. The prior foundation has 41 host tests. No physical phone was connected. Windows/Linux Python 3.11–3.14 CI now also runs native Tk smoke tests; see the actual final-commit Actions result and [BUILD_STATUS.md](BUILD_STATUS.md). A GUI source launch is not a packaged Windows EXE or Android runtime test.

## Try the developer tools

Run from the repository root with Python 3.11 or newer. No third-party Python packages are needed; the GUI requires Tk and a graphical desktop.

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos.studio
```

`gate` deliberately exits with code **2** while publication is blocked; this is expected, not a failed host test. Errors exit with code 1. See [Flash Studio instructions](docs/FLASH_STUDIO.md) for native GUI testing, export behavior and current limitations.

Optional read-only inspection requires your own trusted Android SDK Platform Tools, an authorized USB-debugging connection and exactly one USB phone. Supply an absolute executable path; the tool does not search PATH, download binaries or install drivers.

```powershell
python -m swirphoneos inspect --adb "C:\Android\platform-tools\adb.exe"
```

```sh
python -m swirphoneos inspect --adb /opt/android/platform-tools/adb
```

The paths are examples. Inspection does not enable USB debugging, unlock, reboot, root, erase or write the phone. ADB may start its local host server. Manufacturer/model/bootloader/Treble values are device-reported hints, not trusted hardware identification or proof of GSI compatibility. Missing information stays unknown. No serial/IMEI property is requested. Device-reported values must still be reviewed before sharing a report publicly; nothing uploads automatically.

## Product direction

**SwirPhoneOS Core:** maintainable AOSP/Linux integration, ARM64 GSI where compatible, device-specific ports where necessary, custom launcher/SystemUI/settings, polished dark/neon visual design, privacy controls and signed OTA updates. Android app compatibility is a goal; Google services and individual apps are not guaranteed.

**SwirPhoneOS Flash Studio:** a Windows-first, Linux-capable desktop companion. The first read-only GUI slice is implemented. Planned next capabilities include explicit device packs, Fastboot/FastbootD diagnostics, verified downloads, pre-flight checks, user-confirmed installation, a transaction journal and tested per-device recovery. Packaged EXE delivery and live USB verification remain outstanding.

**First planned reference:** OnePlus Nord AC2003 (`avicii`). Its profile is explicitly `PLANNED_NOT_SUPPORTED`, with no firmware baseline, validated partition map or flash operations. Metadata is not a working port.

## Safety and release policy

There is no universal installer for every Android phone. Treble support alone is insufficient. Unlocking a bootloader can erase user data; full backups and stock restoration cannot be promised for every device. No unattended physical-device modification is authorized by this project automation. See [SECURITY.md](SECURITY.md) and [upstream sources](docs/SOURCES.md).

A beta Release must contain a usable tested system image and verified Windows companion, not a renamed source ZIP. [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) requires exact-build hardware, install/recovery, security and artifact evidence. No beta is published now.

## Development

This repository is the sole source of truth for the mobile project previously called SwirOS foundation v0.0.1. It is separate from SWIR OS Desktop, Konofix and KaliPhoneStudio. Repository-facing content is English, with localized runtime translation catalogs; progress reports to the owner are Polish. Scheduled development must follow [AGENTS.md](AGENTS.md), not inflate completion or claim unattended continuous computation.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Licensing policy](LICENSES.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
