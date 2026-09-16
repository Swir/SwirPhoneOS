# Changelog

## Unreleased

### Reproducible AOSP workspace and resolved-manifest evidence

Added a fail-closed AOSP workspace contract around the pinned Android 17 baseline. `python -m swirphoneos aosp-plan` now emits an argv-oriented exact-tag Repo init/sync, resolved-manifest capture, product staging and Cuttlefish build plan without executing it or claiming build success. `python -m swirphoneos aosp-manifest` validates a captured `repo manifest -r` snapshot, requires every project revision to be a full 40-character Git SHA and reports a SHA-256 digest for reproducibility evidence.

Added explicit product staging with a dry-run default. `stage-product --execute` copies only the two checked-in product makefiles into `vendor/swir/products/` and refuses to mutate a directory that does not look like an initialized AOSP checkout (`.repo/` plus `build/envsetup.sh`). The operation never talks to a phone or enables Fastboot writes. Added host tests, CI validation and `docs/AOSP_BUILD_WORKSPACE.md`. No Android source sync, Kati/Soong build or Cuttlefish boot is claimed, so weighted progress remains **2%** and Beta remains **0/9**.

### Unified SwirPhoneStudio diagnostics and first Cuttlefish product slice

Integrated the existing strict read-only ADB and Fastboot/FastbootD cores into a single SwirPhoneStudio workflow. The GUI can now select either transport, runs the same bounded asynchronous inspection contract, clears stale results on transport changes and exports a unified schema-v2 report. Device-reported values can be compared with the local metadata-only profile registry, but matches remain hints only: `identity_verified: false`, `swirphoneos_support: NOT_VALIDATED` and `flash_allowed: false` are enforced. Ambiguous matches expose no candidate. Added the equivalent `inspect-device` CLI path and negative tests for safety/provenance tampering.

Updated the Windows PyInstaller package contract to bundle `device_packs` alongside localization data so the frozen developer GUI can use the same profile metadata without downloading anything. No installation/write control was added and no physical USB compatibility is claimed.

Added the first checked-in SwirPhoneOS Android product integration slice under `platform/aosp_product/`. The product inherits the standard AOSP x86_64-only Cuttlefish phone configuration, registers `swirphoneos_cf_x86_64-aosp_current-userdebug`, applies Swir product identity, and deliberately does not weaken root, Verified Boot or signing policy. Added an offline validator and CI command `python -m swirphoneos product-contract`. This is product-source scaffolding only: no source sync, Kati/Soong build, Cuttlefish boot or Android artifact is claimed. Project progress remains **2%** and Beta remains **0/9**.

### Pinned Android 17 baseline, build-host preflight and Windows package pipeline

Advanced the Android 17 baseline to exact official release-tag pinning. `platform/aosp_baseline.json` is schema v2 / `PINNED_NOT_BUILT` and records `android-17.0.0_r1`, annotated tag object `7a9e46ba6ed424f922a3457f4964e67e0b966201`, manifest commit `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f` and tree `1541b7154f1532032baf7c73f222256cc29e8cfb`. No AOSP source sync or Android build is claimed.

Added a bounded read-only AOSP host preflight for Linux/x86-64, glibc, workspace capacity, RAM, Git/Repo and KVM visibility. It installs nothing, downloads nothing and does not start a build.

Added a Windows x64/Python 3.14 SwirPhoneStudio packaging workflow using pinned PyInstaller 6.22.3. It creates a one-file developer executable, smoke-tests the frozen GUI, records SHA-256 and uploads a short-lived CI artifact. This is not a beta/release or hardware validation.

### Global localization, app registry and SwirRoot safety contracts

Moved Flash Studio localization to validated data catalogs and expanded current desktop strings to English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Added locale normalization, English fallback, placeholder-parity validation, duplicate-key rejection, LTR/RTL metadata and machine-readable coverage. This does not yet claim complete mobile localization or RTL runtime support.

Added `system_apps/manifest.json` plus strict validation for the complete 20-app first-party suite. The registry fixes the `org.swir.phoneos.*` namespace, delivery phase, hardware dependence, beta-critical status and capability contract. Every current entry is `HOST_CONTRACT`; no Android application package is claimed as implemented.

Added the executable SwirRoot fail-closed policy contract in `swirroot/policy.json` and `swirphoneos/swirroot.py`. Unverified builds remain `UNAVAILABLE`; authorization is deny-by-default; rollback material, journaling, exact-build/profile checks and owner confirmation are mandatory; exploit/bypass methods are forbidden. Write operations are disabled and supported root builds remain zero.

### First-party system application scope

Defined the canonical first-party suite: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. The product requirement includes an original SwirPhoneOS visual language, icons, localization, accessibility, permissions and system integration. Static shells do not count as implemented apps.

### Read-only Fastboot/FastbootD diagnostics and multi-device registry

Added a strictly read-only Fastboot/FastbootD diagnostic core with an explicit trusted executable, one local USB device, a tiny `getvar` allowlist and identity recheck. It never requests serial-number variables and rejects write commands.

Added strict schema-v1 validation for `device_packs/<vendor>/<codename>/profile.json`. Safe IDs, model allowlists, HTTPS sources and duplicate-profile checks are enforced. Schema v1 cannot authorize writes. The OnePlus Nord AC2003 (`avicii`) profile remains `PLANNED_NOT_SUPPORTED`.

### Android 17 AOSP discovery

Recorded the Android 17 / API 37 candidate and upstream release identity. The discovery state was superseded by the exact pinned baseline described above. No source sync or platform build was claimed.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

### Read-only Flash Studio desktop slice

Added the Python/Tk desktop companion with dark blue styling, the project icon, trusted ADB selection, asynchronous read-only inspection, elapsed status, read-only report display, create-only local JSON export and `by Swir` GitHub footer. Added initial English, Polish and Norwegian Bokmal catalogs with native locale detection and English fallback. Failed scans invalidate previous exports and raw exception/device details stay private.

Added native Linux/Windows Tk smoke coverage to the Python 3.11–3.14 host CI matrix. This work did not include an Android image or physical-phone validation. Progress remained 2%; beta remained 0/9.

### Initial foundation

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics, weighted progress accounting, strict mandatory beta-gate validation, a hard publication guard, Windows/Linux host CI, original branding/icon assets, architecture/safety documentation and an explicitly unsupported avicii metadata profile.

## 0.0.1 — Initial concept archive

The earlier SwirOS planning package was not a bootable OS, installer or hardware-supported release. Its scope continues here with corrected safety and readiness distinctions.
