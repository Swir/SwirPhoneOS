<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, Windows EXE, installer, backup or stock-restore implementation is available yet. The runnable component is read-only Python host diagnostics.

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

The `swirphoneos` Python package provides selected read-only **ADB** property inspection plus a separate read-only **Fastboot/FastbootD** inspection path. Both use explicit trusted Android SDK executable paths, strict single-device selection, tiny command allowlists, private error messages, unknown-state handling and a second transport identity check. The Fastboot path queries only `product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace` and `secure`; it never requests serial-number variables and rejects mutating commands. Reports never authorize flashing.

The status command validates the weighted roadmap and mandatory beta gate ledger. Publication remains disabled even if someone manually checks every ledger box: an independent candidate/artifact/evidence verifier is still required.

The last verified main baseline recorded 41 local Linux/Python 3.13.5 unit tests plus compile and CLI smoke checks. New Fastboot diagnostics are additionally covered by host-side mocks in their feature PR. No physical phone has been validated. Windows/Linux Python 3.11–3.14 are CI targets; a green host matrix still does not establish phone compatibility. See [BUILD_STATUS.md](BUILD_STATUS.md).

## Try the developer tools

Run from the repository root with Python 3.11 or newer. No third-party Python packages are needed.

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
```

`gate` deliberately exits with code **2** while publication is blocked; this is expected, not a failed host test. Errors exit with code 1.

### Read-only ADB inspection

Optional ADB inspection requires your own trusted Android SDK Platform Tools, an authorized USB-debugging connection and exactly one USB phone. Supply an absolute executable path; the tool does not search PATH, download binaries or install drivers.

```powershell
python -m swirphoneos inspect --adb "C:\Android\platform-tools\adb.exe"
```

```sh
python -m swirphoneos inspect --adb /opt/android/platform-tools/adb
```

### Read-only Fastboot / FastbootD inspection

With exactly one phone already placed in Fastboot or FastbootD mode, use the trusted `fastboot` binary explicitly:

```powershell
python -m swirphoneos inspect-fastboot --fastboot "C:\Android\platform-tools\fastboot.exe"
```

```sh
python -m swirphoneos inspect-fastboot --fastboot /opt/android/platform-tools/fastboot
```

The diagnostic command itself does **not** reboot the phone into Fastboot, unlock the bootloader, erase data, change slots, boot an image, flash, format, relock or restore anything. Unsupported variables remain unknown rather than being treated as proof of support.

The paths above are examples. Manufacturer/model/bootloader/Treble/Fastboot values are device-reported hints, not trusted hardware identification or proof of GSI compatibility. Missing information stays unknown. No serial/IMEI property is requested or intentionally included in JSON reports.

## Product direction

**SwirPhoneOS Core:** maintainable AOSP/Linux integration, ARM64 GSI where compatible, device-specific ports where necessary, custom launcher/SystemUI/settings, polished dark/neon visual design, privacy controls and signed OTA updates. Android app compatibility is a goal; Google services and individual apps are not guaranteed.

**SwirPhoneOS Flash Studio:** a Windows-first, Linux-capable desktop companion. Planned features include read-only diagnostics, explicit device packs, verified downloads, pre-flight checks, user-confirmed installation, a transaction journal and tested per-device recovery. The future GUI must use the system language with English fallback, a custom application icon and a `by Swir` GitHub footer.

**First planned reference:** OnePlus Nord AC2003 (`avicii`). Its profile is explicitly `PLANNED_NOT_SUPPORTED`, with no firmware baseline, validated partition map or flash operations. Metadata is not a working port.

## Compatibility strategy

SwirPhoneOS is designed around a shared AOSP/GSI-capable core plus explicit device packs and, where required, device-specific ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ.

The long-term goal is therefore **broad Android-device coverage through automatic detection and validated profiles**, not pretending that unknown hardware is safe to flash. Devices with permanently locked bootloaders or unavailable vendor/kernel support may remain unsupported.

## Safety and release policy

There is no universal installer for every Android phone. Treble support alone is insufficient. Unlocking a bootloader can erase user data; full backups and stock restoration cannot be promised for every device. No unattended physical-device modification is authorized by this project automation. See [SECURITY.md](SECURITY.md) and [upstream sources](docs/SOURCES.md).

A beta Release must contain a usable tested system image and verified Windows companion, not a renamed source ZIP. [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) requires exact-build hardware, install/recovery, security and artifact evidence. No beta is published now.

## Development

This repository is the sole source of truth for the mobile project previously called SwirOS foundation v0.0.1. It is separate from SWIR OS Desktop, Konofix and KaliPhoneStudio. Repository-facing content is English; progress reports to the owner are Polish. Scheduled development must follow [AGENTS.md](AGENTS.md), not inflate completion or claim unattended continuous computation.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Licensing policy](LICENSES.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
