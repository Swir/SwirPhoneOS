<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, Windows EXE, installer, backup or stock-restore implementation is available yet. The runnable host side is a read-only Python CLI plus an early SwirPhoneStudio diagnostic GUI.

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

A strict **device profile registry** validates metadata in `device_packs/<vendor>/<codename>/profile.json`. Schema v1 is deliberately non-executable: it rejects `flash_enabled: true`, rejects flash operations, requires a safe `vendor/codename` ID, validates model allowlists and HTTPS sources, and detects duplicate profile IDs. This lets the project grow toward broad multi-device support without treating an unknown phone as safe to flash.

The first **SwirPhoneStudio** GUI source is now present. It wraps the same read-only diagnostics, automatically chooses Polish, Norwegian or English from the OS locale with English fallback, shows JSON results, provides a `by Swir` GitHub footer and exports privacy-checked JSON reports. The export layer rejects sensitive identifier fields such as serial/IMEI/MEID. This is an early developer GUI, not a Windows EXE or installer, and it has not yet passed a physical Windows/USB smoke test.

The platform layer now records an **Android 17 / API 37 AOSP baseline candidate**. At the 2026-09-16 check, AOSP's recommended `android-latest-release` manifest resolved to `android17-release`; the candidate record references `android-17.0.0_r1` / `CP2A.260605.016`. Its status is deliberately `CANDIDATE_NOT_PINNED`: no source sync or Android build is claimed. See [docs/UPSTREAM_BASELINE.md](docs/UPSTREAM_BASELINE.md).

The status command validates the weighted roadmap and mandatory beta gate ledger. Publication remains disabled even if someone manually checks every ledger box: an independent candidate/artifact/evidence verifier is still required.

The last verified main baseline recorded 41 local Linux/Python 3.13.5 unit tests plus compile and CLI smoke checks. New Fastboot/profile/i18n/report/platform code adds host-side tests in its feature PR. No physical phone has been validated. Windows/Linux Python 3.11–3.14 are CI targets; a green host matrix still does not establish phone compatibility. See [BUILD_STATUS.md](BUILD_STATUS.md).

## Try the developer tools

Run from the repository root with Python 3.11 or newer. No third-party Python packages are needed for the CLI. The GUI requires a Python build with Tk support.

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos studio
```

`profiles` validates and lists the current metadata-only device registry. `baseline` validates and prints the offline AOSP candidate metadata without downloading source. Neither command authorizes flashing. `studio` opens the read-only SwirPhoneStudio developer UI when Tk is available. `gate` deliberately exits with code **2** while publication is blocked; this is expected, not a failed host test. Errors exit with code 1.

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

**SwirPhoneOS Core:** maintainable AOSP/Linux integration, beginning from a reproducibly pinned Android 17 candidate after build-host preflight; ARM64 GSI where compatible; device-specific ports where necessary; custom launcher/SystemUI/settings; polished dark/neon visual design; privacy controls; and signed OTA updates. Android app compatibility is a goal; Google services and individual apps are not guaranteed.

**SwirPhoneStudio:** a Windows-first, Linux-capable desktop companion for diagnostics, installation and recovery. Its first developer GUI is read-only. Planned later stages add signed/verified downloads, pre-flight checks, explicit device packs, user-confirmed installation plans, a transaction journal and tested per-device recovery before any write controls are enabled. The application uses the system language where a translation exists, falls back to English, keeps the project icon for packaging and includes the `by Swir` GitHub footer.

**First planned reference:** OnePlus Nord AC2003 (`avicii`). Its profile is explicitly `PLANNED_NOT_SUPPORTED`, with no firmware baseline, validated partition map or flash operations. Metadata is not a working port.

## Compatibility strategy

SwirPhoneOS is designed around a shared AOSP/GSI-capable core plus explicit device packs and, where required, device-specific ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ.

The long-term goal is therefore **broad Android-device coverage through automatic detection and validated profiles**, not pretending that unknown hardware is safe to flash. Devices with permanently locked bootloaders or unavailable vendor/kernel support may remain unsupported.

## Safety and release policy

There is no universal installer for every Android phone. Treble support alone is insufficient. Unlocking a bootloader can erase user data; full backups and stock restoration cannot be promised for every device. No unattended physical-device modification is authorized by this project automation. See [SECURITY.md](SECURITY.md) and [upstream sources](docs/SOURCES.md).

A beta Release must contain a usable tested system image and verified Windows companion, not a renamed source ZIP. [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) requires exact-build hardware, install/recovery, security and artifact evidence. No beta is published now.

## Development

This repository is the sole source of truth for the mobile project previously called SwirOS foundation v0.0.1. It is separate from SWIR OS Desktop, Konofix and KaliPhoneStudio. Repository-facing documentation is English; application translations may be multilingual; progress reports to the owner are Polish. Scheduled development must follow [AGENTS.md](AGENTS.md), not inflate completion or claim unattended continuous computation.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [AOSP baseline](docs/UPSTREAM_BASELINE.md) · [Licensing policy](LICENSES.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
