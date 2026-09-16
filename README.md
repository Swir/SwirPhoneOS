<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, installer, backup or stock-restore implementation is available yet. Runnable components are read-only Python host diagnostics and SwirPhoneStudio; Windows packaging is a developer CI pipeline, not a beta release.

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

Each bar segment represents a completed 5 percentage points, rounded down. [project.json](project.json) is the machine-readable ledger and [ROADMAP.md](ROADMAP.md) defines weights/evidence. Host tests, desktop packaging and metadata contracts do not complete Android build or hardware gates. **Beta: 0/9 gates passed.**

## What works now

### Safety-first device inspection

The `swirphoneos` Python package provides strictly read-only **ADB** and **Fastboot/FastbootD** diagnostics. Both require an explicit trusted Android SDK executable, require exactly one local USB phone, hide raw transport errors and expose no write command. Fastboot is limited to a small `getvar` allowlist (`product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace`, `secure`). No reboot, unlock, erase, slot change, boot, flash, format, root, relock or restore path is enabled.

A strict **device profile registry** validates metadata under `device_packs/<vendor>/<codename>/profile.json`. Schema v1 is deliberately non-executable: `flash_enabled: true` and executable flash operations are rejected. The OnePlus Nord AC2003 (`avicii`) entry remains `PLANNED_NOT_SUPPORTED`.

The new **profile-assessment layer** can compare device-reported ADB/Fastboot values with local profile metadata and return a profile *hint*. A hint is never trusted identity: `identity_verified` stays `false`, `swirphoneos_support` stays `NOT_VALIDATED`, and `flash_allowed` stays `false`. Ambiguous matches expose no candidate. Firmware, partition, recovery and physical-device evidence are still required before a profile can become supported.

### SwirPhoneStudio

SwirPhoneStudio has a runnable dark/blue desktop GUI with the custom SwirPhoneOS icon, language selector, **ADB/Fastboot transport selector**, explicit trusted-tool selection, asynchronous inspection, read-only JSON report view, create-only local export and a `by Swir` GitHub footer. The default GUI now uses the same fail-closed unified report/profile-hint contract as the CLI.

A Windows x64/Python 3.14 PyInstaller workflow creates a one-file `SwirPhoneStudio.exe`, bundles localization data and the metadata-only device profile registry, smoke-tests the frozen GUI, records SHA-256 and uploads a short-lived CI artifact. This is developer packaging verification only; it is not a release or hardware certification.

### Global localization

Host localization is data-driven with system-locale detection and English fallback. Current desktop catalogs cover English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Arabic establishes RTL metadata. The mobile contract extends this to setup, launcher, SystemUI, Settings, recovery, updater, SwirRoot and all bundled applications, including locale-specific date/time/number/unit formatting, fonts/scripts, input methods, plural rules, accessibility labels and RTL mirroring. See [docs/I18N.md](docs/I18N.md).

### Android 17 platform foundation

The platform layer preserves an exact **Android 17 / API 37 AOSP release pin**: `android-17.0.0_r1` / build `CP2A.260605.016`, with the pinned manifest tag/commit/tree recorded in [platform/aosp_baseline.json](platform/aosp_baseline.json). Status remains **`PINNED_NOT_BUILT`**: no AOSP source sync or Android build is claimed.

A bounded read-only build-host preflight checks the Linux/x86-64 environment, glibc, workspace capacity, RAM, Git/Repo and KVM visibility without installing packages, downloading source or starting a build.

The repository now also contains the first **SwirPhoneOS Cuttlefish product integration skeleton** under [platform/aosp_product](platform/aosp_product). It inherits the standard AOSP x86_64-only Cuttlefish phone product and registers `swirphoneos_cf_x86_64-aosp_current-userdebug`. An offline validator checks the product registration, inheritance and Swir identity and rejects obvious security/signing weakening. This is source integration scaffolding only; Kati/Soong build and Cuttlefish boot evidence are still required.

### System apps and SwirRoot contracts

A machine-readable registry defines the complete 20-app first-party suite under `org.swir.phoneos.*`: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Every app is still `HOST_CONTRACT`; no Android APK is claimed as implemented yet. See [docs/SYSTEM_APPS.md](docs/SYSTEM_APPS.md).

SwirRoot is currently a **fail-closed engineering policy**, not an enabled root implementation. Unverified builds remain `UNAVAILABLE`; authorization is deny-by-default; rollback material, operation journaling, exact-build/profile checks and explicit owner confirmation are mandatory; exploit/bypass methods are forbidden; write operations are disabled; supported root builds = 0. See [docs/SWIRROOT.md](docs/SWIRROOT.md).

## Developer commands

Run from the repository root with Python 3.11 or newer. Host validators use only the standard library; the GUI additionally requires Tk and a graphical desktop.

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos product-contract
python -m swirphoneos build-preflight --workspace /absolute/path/to/aosp-workspace
python -m swirphoneos i18n
python -m swirphoneos apps
python -m swirphoneos root-policy
python -m swirphoneos.studio
```

Read-only ADB inspection:

```powershell
python -m swirphoneos inspect --adb "C:\Android\platform-tools\adb.exe"
python -m swirphoneos inspect-device --transport adb --tool "C:\Android\platform-tools\adb.exe"
```

Read-only Fastboot/FastbootD inspection:

```powershell
python -m swirphoneos inspect-fastboot --fastboot "C:\Android\platform-tools\fastboot.exe"
python -m swirphoneos inspect-device --transport fastboot --tool "C:\Android\platform-tools\fastboot.exe"
```

`inspect-device` adds only a non-authoritative local profile hint to the strict transport report. It cannot certify a phone or authorize a write. `product-contract` validates checked-in AOSP product scaffolding without building Android. `gate` deliberately exits with code **2** while beta publication is blocked.

## Product direction

**SwirPhoneOS Core:** Linux kernel + AOSP/Android-compatible userspace/HAL integration, a shared core where practical, device-specific packs/ports where required, original Swir UI/services/apps, Android application compatibility, privacy controls and signed OTA updates.

**SwirPhoneStudio:** Windows-first, Linux-capable desktop companion for device detection, verified downloads, backup/install planning, transaction journaling, recovery and stock restore. Write controls remain disabled until exact per-device safety gates are implemented and physically verified.

**SwirRoot:** first-party owner-controlled root enable/disable for explicitly supported SwirPhoneOS builds, with backup/rollback, diagnostics, per-app authorization and a tested unroot path. It must not break locked bootloaders or OEM protections through exploits.

**Worldwide use:** every system surface and bundled app must use the shared localization architecture, detect the best locale on first setup and fall back to English when needed.

## Compatibility strategy

SwirPhoneOS targets broad Android-device coverage through a shared AOSP/GSI-capable core plus validated per-device profiles and ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ. Unknown hardware therefore remains unsupported until evidence exists.

The first planned reference device is OnePlus Nord AC2003 (`avicii`), but its current metadata profile is explicitly **not supported**. Devices with permanently locked bootloaders or unavailable kernel/vendor support may remain unsupported.

## Safety and beta policy

Treble support alone is not proof of compatibility. Unlocking a bootloader can erase data, and backup/restore capability differs by device. No unattended physical-device modification is authorized by the project automation. See [SECURITY.md](SECURITY.md).

A beta Release requires a reproducible OS build, a real boot path, safe install/rollback/recovery, at least one physically verified supported phone profile, usable core system functionality and verified release artifacts/checksums. Telephony/camera capability must be stated per tested device. [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) remains authoritative. **No beta is published now.**

## Development

This repository is the canonical source of truth for SwirPhoneOS. Repository-facing content is English; runtime localization is data-driven; owner progress reports are Polish. Scheduled development follows [AGENTS.md](AGENTS.md) and must not inflate completion or claim tests that did not run.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Build status](BUILD_STATUS.md) · [System Apps](docs/SYSTEM_APPS.md) · [Global i18n](docs/I18N.md) · [SwirRoot](docs/SWIRROOT.md) · [Changelog](CHANGELOG.md) · [AOSP baseline](docs/UPSTREAM_BASELINE.md) · [Licensing policy](LICENSES.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
