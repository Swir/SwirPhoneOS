# Changelog

## Unreleased

### Pinned Android 17 baseline, build-host preflight and Windows package pipeline

Advanced the Android 17 baseline from moving discovery metadata to exact official release-tag pinning. `platform/aosp_baseline.json` is now schema v2 / `PINNED_NOT_BUILT` and records `android-17.0.0_r1`, annotated tag object `7a9e46ba6ed424f922a3457f4964e67e0b966201`, manifest commit `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f` and tree `1541b7154f1532032baf7c73f222256cc29e8cfb`. The validator rejects partial pin metadata and cannot mark the baseline `BUILT_VERIFIED` without complete pin data plus actual source acquisition/build completion. No AOSP source sync or Android build is claimed.

Added a bounded read-only AOSP host preflight. It checks Linux/x86-64, glibc 2.17+, at least 400 GiB workspace capacity, 64 GiB RAM for the full-build gate, Git/Repo presence and KVM visibility without installing packages, downloading source, changing host configuration or starting a build. Added deterministic synthetic tests and a `python -m swirphoneos build-preflight --workspace <path>` CLI surface. Passing this preflight is not build evidence.

Added a Windows x64/Python 3.14 SwirPhoneStudio packaging workflow using pinned PyInstaller 6.22.3. It produces a one-file developer executable from the existing read-only GUI, includes the data-driven localization catalog, smoke-tests the frozen GUI, records SHA-256 and uploads a short-lived CI artifact. This is a developer artifact pipeline, not a beta/release or physical-device validation. Project progress remains 2%; beta remains 0/9.

### Global localization, app registry and SwirRoot safety contracts

Moved Flash Studio localization from Python literals into a validated data catalog and expanded the current desktop strings to eight locales: English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Added BCP-47-style normalization, English fallback, placeholder-parity validation, duplicate-key rejection, explicit LTR/RTL metadata and machine-readable coverage via `python -m swirphoneos i18n`. Arabic establishes the first RTL catalog metadata path; this does not yet claim complete mobile RTL layout support.

Added `system_apps/manifest.json` plus a strict validator for the complete 20-app first-party suite. The registry fixes the `org.swir.phoneos.*` namespace, delivery phase, hardware dependence, beta-critical status and capability contract for each app. Every current entry is `HOST_CONTRACT`: CI rejects missing essential apps, foreign/duplicate packages and invalid hardware-verification claims. No Android application package is claimed as implemented yet.

Added the first executable SwirRoot safety contract in `swirroot/policy.json` and `swirphoneos/swirroot.py`. Unverified builds must remain `UNAVAILABLE`; authorization is deny-by-default; rollback material, journaling, exact-build/profile checks and owner confirmation are mandatory. Exploit/bypass methods are explicitly forbidden. Current write operations are disabled and there are zero supported root builds, so `root_available` remains false. CI now validates localization, app-registry and SwirRoot contracts on every host matrix job.

### First-party system app suite and SwirRoot scope

Defined the canonical SwirPhoneOS first-party application suite in `docs/SYSTEM_APPS.md`: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Added a shared product requirement for original SwirPhoneOS visual language, icons, localization, accessibility, permissions and system integration. The roadmap now separates emulator-capable core apps from hardware-dependent telephony/camera work so static mockups cannot be counted as implementation.

Defined SwirRoot as an owner-controlled first-party root manager for explicitly supported SwirPhoneOS builds/device profiles. Its design requires authoritative root state, explicit confirmation, verified rollback material, operation journaling, a tested unroot path, deny-by-default per-app authorization when the root service exists, and integration with Swir Update/recovery/SwirPhoneStudio. It must not bypass locked bootloaders or OEM protections through exploits. This is product/architecture scope only: no root implementation or working Android system app is claimed, and project progress remains 2%.

### Read-only Fastboot/FastbootD diagnostics

Added a strictly read-only Fastboot/FastbootD diagnostic core. It requires an explicit trusted Android SDK `fastboot` executable, exactly one local USB device and a small `getvar` allowlist (`product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace`, `secure`). It rejects every command outside that allowlist, never requests serial-number variables, rechecks device identity after inspection and always returns `flash_allowed: false`. Added portable mocked tests and the CLI command `python -m swirphoneos inspect-fastboot --fastboot <absolute-path>`.

### Metadata-only multi-device registry

Added strict schema-v1 validation for `device_packs/<vendor>/<codename>/profile.json` plus a `profiles` CLI command. Safe IDs, bounded model allowlists, HTTPS sources and duplicate profile detection are enforced. Schema v1 cannot authorize writes: `flash_enabled: true` and non-empty flash operations are rejected. The existing OnePlus Nord AC2003 (`avicii`) profile remains `PLANNED_NOT_SUPPORTED`.

### Android 17 AOSP baseline discovery

Added an offline Android 17 / API 37 baseline candidate record and validator. At the 2026-09-16 upstream check, `android-latest-release` resolved to `android17-release`; the candidate references `android-17.0.0_r1` / `CP2A.260605.016`. This discovery state was subsequently superseded by the exact pin described above. No AOSP source sync or platform build is claimed.

This work extends host diagnostics and platform planning only. It does not add supported phones, write-capable installation, bootloader unlocking, image booting, stock restore or beta readiness. Project progress remains 2%; beta gates remain 0/9.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

### Read-only Flash Studio desktop slice

Added a runnable Python/Tk desktop companion with dark blue styling, the project icon, trusted ADB file selection, asynchronous read-only inspection, elapsed status, read-only report display, create-only local JSON export and the `by Swir` GitHub footer. Added extensible English, Polish and Norwegian Bokmal catalogs with native language detection and English fallback. The GUI never invokes Tk from the worker thread. Duplicate scans are rejected, failed scans invalidate previous exports, and raw exception details stay private. Export validation rejects extra fields, changed safety/provenance flags and invalid values; existing files and target symlinks are not overwritten. Reports do not upload automatically.

Added 46 desktop tests, including 7 real Tk-window tests with synthetic inspection. All 46 passed locally on Linux/Python 3.13.5. Added native Linux/Windows GUI smoke checks to the existing Python 3.11–3.14 CI matrix. This is source-level desktop runtime work, not an EXE, Android image or physical-phone validation. Progress remains 2%; beta gates remain 0/9.

### Initial foundation

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics with an explicit trusted-tool path, command allowlist, single-device selection, private errors, unknown-state handling and endpoint recheck. Added weighted progress accounting, strict mandatory beta-gate validation and a hard publication guard. Added 41 local host tests and a Windows/Linux Python 3.11–3.14 CI matrix with SHA-pinned Actions and read-only permissions. Added an original vector application icon, architecture, safety policy, development instructions and an explicitly unsupported avicii metadata profile.

The initial foundation did not include a GUI; the desktop slice above adds it. No Android image, live-phone validation, Windows EXE or installation/restore capability is claimed.

## 0.0.1 — Initial concept archive

The earlier SwirOS ZIP contained planning documentation. It was not a bootable OS, installer or hardware-supported release. Its scope is continued here with corrected safety and readiness distinctions.
