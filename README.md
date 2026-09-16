<p align="center"><img src="branding/swirphoneos.svg" width="136" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Developer foundation, not a ROM release.** No bootable SwirPhoneOS image, supported phone, installer, backup or stock-restore implementation is available yet. Runnable components are host-side diagnostics and SwirPhoneStudio. Meaningful Android application source exists, but no APK/runtime claim is made before a real pinned-AOSP build and boot.

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

The canonical ledger is [`project.json`](project.json). Host tests, desktop packaging, source scaffolding and static application source do not complete Android build, boot or hardware gates. **Beta: 0/9 gates passed.**

## What works now

### Safety-first device inspection

The `swirphoneos` Python package provides strictly read-only ADB and Fastboot/FastbootD diagnostics. It accepts only an explicitly selected trusted Android SDK executable, requires one local USB device and exposes no unlock, erase, boot, flash, root, relock or restore command. Device profile matching is a non-authoritative hint only; support and write permission remain false until exact-device evidence exists.

### SwirPhoneStudio

SwirPhoneStudio is a runnable dark/blue desktop GUI with the custom SwirPhoneOS icon, OS-language startup, language selector, ADB/Fastboot transport selection, explicit trusted-tool selection, asynchronous inspection, read-only JSON report view and a `by Swir` GitHub footer. A Windows x64/Python 3.14 PyInstaller workflow creates and smoke-tests a developer EXE artifact. That workflow is packaging evidence, not a beta release or phone certification.

### Android 17 platform foundation

The current baseline is pinned to **Android 17 / API 37** at `android-17.0.0_r1`. The exact manifest identity is recorded in [`platform/aosp_baseline.json`](platform/aosp_baseline.json). Status remains `PINNED_NOT_BUILT`: no completed AOSP source sync, Kati/Soong build or Cuttlefish boot is claimed.

The repository contains a SwirPhoneOS x86_64 Cuttlefish product definition and a reproducible workspace/evidence toolchain. `aosp-plan` emits the exact-tag Repo/build plan; `aosp-manifest` validates a captured `repo manifest -r`; and `stage-product` stages only manifest-whitelisted files under `vendor/swir/` into an already initialized AOSP checkout. None of these tools writes to a phone.

### Functional Android application sources

Six first-party applications are now wired into `PRODUCT_PACKAGES` as meaningful **`ANDROID_SOURCE`**. They are deliberately not `ANDROID_RUNTIME` until the pinned AOSP product builds and the apps are exercised in Cuttlefish.

**SwirCalculator** (`org.swir.phoneos.calculator`) provides a pure-Java BigDecimal engine for basic arithmetic, decimals, sign, percent, backspace and divide-by-zero handling, an original vector icon and dark/cyan UI, locale-aware decimal display, RTL-aware layout and accessibility descriptions. It requests no Android permissions and has a dependency-free host Java engine test. Scientific mode remains unfinished.

**SwirSettings** (`org.swir.phoneos.settings`) provides an original dark/cyan settings hub, localized search, real device/build status and permission-free hand-off to a reviewed allowlist of authoritative Android settings pages. Its pure-Java route catalog is host-tested and unreviewed settings actions fail validation.

**SwirFiles** (`org.swir.phoneos.files`) is a beta-critical permission-free file manager source built around Android's user-granted Storage Access Framework. It keeps persistent access only to a directory the owner chooses, browses/searches that tree, creates folders and uses provider-supported rename/copy/move/delete operations with an explicit delete confirmation. It also opens and shares granted documents without requesting broad storage permissions. File-name/search policy is host-tested.

**SwirDeviceCare** (`org.swir.phoneos.device_care`) is a beta-critical diagnostics source that reads real framework state without privileged permissions: device/security-patch identity, battery/charging state, data-partition storage usage, memory availability and Android thermal status. Its health calculations are kept in host-tested pure Java.

**SwirUpdate** (`org.swir.phoneos.update`) is a beta-critical read-only update-status source. It shows the real local build fingerprint/security patch, maps build type/tags to a development channel and contains a host-tested SHA-256/RSA detached-signature verification policy with tamper rejection. It has **no network permission, package downloader, staging or recovery-install path**; those capabilities remain blocked until the signed OTA/recovery architecture exists and is runtime-tested.

**SwirPrivacy** (`org.swir.phoneos.privacy`) is a beta-critical permission-free privacy center. It searches and opens only an exact reviewed allowlist of authoritative Android privacy, permission, location, application and special-access settings. Live privacy indicators and access history remain unimplemented platform-integration targets rather than placeholder claims.

All six apps ship Android resources for English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic and follow locale layout direction. Their source, manifests, package identities, permission boundaries, localization parity and AOSP staging are checked in host CI. No APK/Cuttlefish/runtime claim is made yet, so these source milestones do not increase global progress.

### Complete system-app plan and SwirRoot

The machine-readable first-party suite contains 20 applications: Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Fourteen remain `HOST_CONTRACT`; Calculator, Settings, Files, Device Care, Update and Privacy are `ANDROID_SOURCE`; zero are `ANDROID_RUNTIME` or `HARDWARE_VERIFIED`.

SwirRoot remains a fail-closed engineering contract. Unverified builds expose `UNAVAILABLE`; authorization is deny-by-default; rollback material, journaling, exact-build/profile checks and explicit owner confirmation are mandatory; exploit/bypass methods are forbidden; write operations are disabled; supported root builds remain zero.

### Global localization

Host localization is data-driven with system-locale detection and English fallback. The current desktop and six Android source apps use English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic resources. The mobile contract covers first setup, launcher, SystemUI, Settings, recovery, updater, SwirRoot and all bundled apps, including RTL, fonts/scripts, plural rules, accessibility and locale-specific formatting.

## Developer commands

Run from the repository root with Python 3.11 or newer:

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
python -m swirphoneos i18n
python -m swirphoneos apps
python -m swirphoneos root-policy
python -m swirphoneos.studio
```

`gate` intentionally exits blocked while mandatory beta evidence is missing. `android-apps` validates checked-in source only and must never be interpreted as build/runtime evidence.

## Product direction

**SwirPhoneOS Core:** Linux kernel + AOSP/Android-compatible userspace/HAL integration, a shared core where practical, device-specific packs/ports where required, original Swir UI/services/apps, Android application compatibility, privacy controls and signed OTA updates.

**SwirPhoneStudio:** Windows-first, Linux-capable desktop companion for device detection, verified downloads, backup/install planning, transaction journaling, recovery and stock restore. Write controls remain disabled until exact-device safety gates are implemented and physically verified.

**SwirRoot:** first-party owner-controlled root enable/disable for explicitly supported SwirPhoneOS builds, with verified rollback, diagnostics, per-app authorization and tested unroot/recovery. It does not use bootloader exploits.

**Worldwide use:** every system surface and bundled app uses a shared localization architecture, detects the best locale during setup and falls back to English.

## Compatibility and release policy

SwirPhoneOS targets broad Android-device coverage through a shared AOSP/GSI-capable core plus validated device-specific profiles/ports. A single identical image or flashing sequence cannot safely cover every Android phone because bootloaders, AVB policy, kernels, vendor interfaces, partition layouts and OEM unlock rules differ. Unsupported hardware stays unsupported until evidence exists.

The first planned reference device is OnePlus Nord AC2003 (`avicii`), but it is currently `PLANNED_NOT_SUPPORTED`.

A beta Release requires a reproducible OS build, real boot path, safe install/rollback/recovery, at least one physically verified phone profile, usable core system functionality and verified release artifacts/checksums. Telephony, camera and root capability are stated per tested device/build. **No beta is published now.**

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Build status](BUILD_STATUS.md) · [System Apps](docs/SYSTEM_APPS.md) · [Global i18n](docs/I18N.md) · [AOSP workspace](docs/AOSP_BUILD_WORKSPACE.md) · [SwirRoot](docs/SWIRROOT.md) · [Changelog](CHANGELOG.md)

---
**by Swir** · [GitHub](https://github.com/Swir)
