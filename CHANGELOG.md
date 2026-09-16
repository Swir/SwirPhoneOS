# Changelog

## Unreleased

### First-party system app suite and SwirRoot scope

Defined the canonical SwirPhoneOS first-party application suite in `docs/SYSTEM_APPS.md`: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Added a shared product requirement for original SwirPhoneOS visual language, icons, localization, accessibility, permissions and system integration. The roadmap now separates emulator-capable core apps from hardware-dependent telephony/camera work so static mockups cannot be counted as implementation.

Defined SwirRoot as an owner-controlled first-party root manager for explicitly supported SwirPhoneOS builds/device profiles. Its design requires authoritative root state, explicit confirmation, verified rollback material, operation journaling, a tested unroot path, deny-by-default per-app authorization when the root service exists, and integration with Swir Update/recovery/SwirPhoneStudio. It must not bypass locked bootloaders or OEM protections through exploits. This is product/architecture scope only: no root implementation or working Android system app is claimed, and project progress remains 2%.

### Read-only Fastboot/FastbootD diagnostics

Added a strictly read-only Fastboot/FastbootD diagnostic core. It requires an explicit trusted Android SDK `fastboot` executable, exactly one local USB device and a small `getvar` allowlist (`product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace`, `secure`). It rejects every command outside that allowlist, never requests serial-number variables, rechecks device identity after inspection and always returns `flash_allowed: false`. Added portable mocked tests and the CLI command `python -m swirphoneos inspect-fastboot --fastboot <absolute-path>`.

### Metadata-only multi-device registry

Added strict schema-v1 validation for `device_packs/<vendor>/<codename>/profile.json` plus a `profiles` CLI command. Safe IDs, bounded model allowlists, HTTPS sources and duplicate profile detection are enforced. Schema v1 cannot authorize writes: `flash_enabled: true` and non-empty flash operations are rejected. The existing OnePlus Nord AC2003 (`avicii`) profile remains `PLANNED_NOT_SUPPORTED`.

### Android 17 AOSP baseline discovery

Added an offline Android 17 / API 37 baseline candidate record and validator. At the 2026-09-16 upstream check, `android-latest-release` resolved to `android17-release`; the candidate references `android-17.0.0_r1` / `CP2A.260605.016`. The state is deliberately `CANDIDATE_NOT_PINNED`, with `download_started: false` and `build_completed: false`. Added a reproducible-pinning policy, baseline CLI command, anti-overclaim tests and CI validation. No AOSP source sync or platform build is claimed.

This work extends host diagnostics and platform planning only. It does not add supported phones, write-capable installation, bootloader unlocking, image booting, stock restore, a packaged Windows EXE or beta readiness. Project progress remains 2%; beta gates remain 0/9.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

### Read-only Flash Studio desktop slice

Added a runnable Python/Tk desktop companion with dark blue styling, the project icon, trusted ADB file selection, asynchronous read-only inspection, elapsed status, read-only report display, create-only local JSON export and the `by Swir` GitHub footer. Added extensible English, Polish and Norwegian Bokmal catalogs with native language detection and English fallback. The GUI never invokes Tk from the worker thread. Duplicate scans are rejected, failed scans invalidate previous exports, and raw exception details stay private. Export validation rejects extra fields, changed safety/provenance flags and invalid values; existing files and target symlinks are not overwritten. Reports do not upload automatically.

Added 46 desktop tests, including 7 real Tk-window tests with synthetic inspection. All 46 passed locally on Linux/Python 3.13.5. Added native Linux/Windows GUI smoke checks to the existing Python 3.11–3.14 CI matrix. This is source-level desktop runtime work, not an EXE, Android image or physical-phone validation. Progress remains 2%; beta gates remain 0/9.

### Initial foundation

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics with an explicit trusted-tool path, command allowlist, single-device selection, private errors, unknown-state handling and endpoint recheck. Added weighted progress accounting, strict mandatory beta-gate validation and a hard publication guard. Added 41 local host tests and a Windows/Linux Python 3.11–3.14 CI matrix with SHA-pinned Actions and read-only permissions. Added an original vector application icon, architecture, safety policy, development instructions and an explicitly unsupported avicii metadata profile.

The initial foundation did not include a GUI; the desktop slice above adds it. No Android image, live-phone validation, Windows EXE or installation/restore capability is claimed.

## 0.0.1 — Initial concept archive

The earlier SwirOS ZIP contained planning documentation. It was not a bootable OS, installer or hardware-supported release. Its scope is continued here with corrected safety and readiness distinctions.
