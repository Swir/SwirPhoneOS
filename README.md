<!-- SWIR-README-STANDARD:v1 -->

<div align="center">

<img src="branding/swirphoneos.svg" width="144" alt="SwirPhoneOS icon" />

# ⚡ SwirPhoneOS

### A safety-first Android-compatible mobile OS project with its own apps, services, device profiles and PC companion

**Linux kernel + AOSP userspace • Android 17 foundation • SwirPhoneStudio • SwirRoot • Global i18n**

![AOSP](https://img.shields.io/badge/AOSP-Android_17-02050A?style=for-the-badge&logo=android&logoColor=62E5FF)
![Python](https://img.shields.io/badge/Python-3.11%2B-02050A?style=for-the-badge&logo=python&logoColor=62E5FF)
![Windows](https://img.shields.io/badge/Studio-Windows_x64-02050A?style=for-the-badge&logo=windows11&logoColor=62E5FF)
![Status](https://img.shields.io/badge/Stage-Foundation-02050A?style=for-the-badge&logo=githubactions&logoColor=62E5FF)

![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Roadmap](https://img.shields.io/badge/roadmap-2%25-0088FF?style=flat-square)
![Milestones](https://img.shields.io/badge/milestones-1%2F10-0088FF?style=flat-square)
![Beta gates](https://img.shields.io/badge/beta_gates-0%2F9-orange?style=flat-square)

</div>

<img width="100%" src="https://raw.githubusercontent.com/Swir/Swir/main/assets/power-divider-v4.svg" alt="SWIR electric divider" />

> **Developer foundation — not a ROM release.** There is currently no public bootable SwirPhoneOS image, supported phone, installer or beta release. Android application source and build/evidence infrastructure are real, but runtime/device support is not claimed before real AOSP builds, boot evidence and physical validation exist.

## 📊 Project status

**2% — 1/10 weighted engineering milestones completed. Beta readiness: 0/9 gates passed.**

`[--------------------] 2%`

The authoritative ledger is [`project.json`](project.json). CI, source-ready applications, Windows packaging, read-only hardware evidence and local recovery preparation do **not** substitute for an Android build, Cuttlefish boot or physical-device validation.

| Area | Current verified state |
|---|---|
| Android baseline | `android-17.0.0_r1` / API 37 pinned, not built |
| Cuttlefish product | Source-integrated, not built or booted |
| ARM64 GSI | Source/build-evidence path exists, no real `system.img` evidence yet |
| System apps | 20 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 hardware-verified |
| SwirPhoneStudio | Read-only ADB/Fastboot diagnostics and Windows developer packaging |
| Device support | No supported phone yet; `oneplus/avicii` remains `PLANNED_NOT_SUPPORTED` |
| SwirRoot | Source-stage UI/policy only; mutation backend disabled, supported builds = 0 |
| Release | No beta/public OS release |

See [`BUILD_STATUS.md`](BUILD_STATUS.md) for the detailed evidence matrix.

## 🌐 What is SwirPhoneOS?

SwirPhoneOS is being designed as our own mobile operating system built around the Linux kernel and AOSP/Android-compatible userspace and HAL integration where practical. The architecture uses a shared core plus reviewed device-specific profiles/ports rather than pretending that one generic image or flashing sequence is safe for every Android phone.

The project also includes **SwirPhoneStudio**, a Windows-first PC companion for diagnostics and future recovery/install workflows, plus **SwirRoot**, a first-party owner-controlled root design for explicitly supported builds. Root support must use legitimate unlocked/owner-supported boot or image paths, verified rollback and explicit confirmation; exploit-based bootloader or vendor-protection bypasses are forbidden.

## ✨ Highlights

| Feature | What it provides today |
|---|---|
| ⚙️ Pinned Android 17 foundation | Exact AOSP tag/baseline identity, build planning and reproducibility contracts |
| 🧪 Cuttlefish evidence chain | Exact product identity, boot/runtime/app-smoke collectors prepared for the first real build |
| 📱 20 first-party system apps | Meaningful Android source integrated into `PRODUCT_PACKAGES`, not counted as runtime until actually built/exercised |
| 🖥️ SwirPhoneStudio | Multilingual dark/cyan desktop diagnostics with trusted ADB/Fastboot tool selection and Windows packaging |
| 🛡️ Fail-closed recovery preparation | Exact local artifact hashing, create-only recovery journals and cross-transport read-only hardware correlation |
| 🔐 SwirRoot safety model | Deny-by-default policy, mandatory rollback/journal gates and a new readiness projection that still cannot authorize writes |
| 🌍 Global i18n | EN/PL/NB/DE/ES/FR/PT/AR resources across all 20 current Android source apps with RTL-aware configuration |
| 🧩 Device profiles | Shared core plus exact per-device metadata/ports; unsupported hardware stays unsupported until evidence exists |

## 📱 Essential system apps

All required everyday-app slots have meaningful Android source and are included in the developer product, but all remain below `ANDROID_RUNTIME` until the pinned OS builds and boots.

| App | Source-stage capability |
|---|---|
| Phone | Permission-free keypad + explicit Android `ACTION_DIAL`; in-call/default-role/history still open |
| Contacts | Scoped `READ_CONTACTS`, browse/search, Android-managed edit/create, vCard import/export |
| Messages | Local draft/composer + explicit `ACTION_SENDTO`; no silent SMS, MMS/history still open |
| Camera | Camera2 capability inspection + explicit system photo/video capture hand-off; direct capture unverified |
| Gallery | Scoped MediaStore browse/search/open/share + owner-confirmed delete |
| Files | Storage Access Framework browse/search/create/rename/copy/move/delete/open/share |
| Settings | Searchable Swir hub + reviewed authoritative Android settings routes |
| Browser | HTTPS-first WebView with conservative privacy defaults; downloads still open |
| Clock | Localized clock, foreground stopwatch/timer + visible alarm hand-off |
| Calculator | Host-tested `BigDecimal` basic arithmetic + locale-aware display |
| Notes | App-private SQLite CRUD/search/share + Markdown export |
| Voice Recorder | Foreground-only private AAC/MPEG-4 record/playback/export |
| Calendar | Local SQLite agenda + share/ICS export; provider bridge still open |
| Weather | Bounded Open-Meteo HTTPS current-weather lookup for owner-entered coordinates |
| System Updater | Read-only build/channel state + SHA-256/RSA metadata verification; install disabled |
| Backup/Restore | Bounded owner-selected archive creation + safe inspection; restore orchestration still open |
| Privacy Center | Reviewed routes into Android privacy/permission surfaces |
| Device Care | Framework-backed device/battery/storage/memory/thermal diagnostics |
| Software Center | Local app catalog, version/signing SHA-256 provenance, launch/details hand-off |
| SwirRoot | Owner-facing state/safety UI + non-exported diagnostics; mutation backend disabled |

The machine-readable registry is [`system_apps/manifest.json`](system_apps/manifest.json).

## 🚀 Quick Start — developer tooling

There is no end-user OS installer yet. From a development checkout, use the host validation tools first:

```sh
python -m unittest discover -s tests -v
python -m swirphoneos status
python -m swirphoneos gate
python -m swirphoneos profiles
python -m swirphoneos baseline
python -m swirphoneos product-contract
python -m swirphoneos gsi-contract
python -m swirphoneos android-apps
python -m swirphoneos i18n
python -m swirphoneos apps
python -m swirphoneos root-policy
```

`gate` intentionally remains blocked while mandatory beta evidence is missing.

### AOSP / Cuttlefish planning

```sh
python -m swirphoneos build-preflight --workspace /path/to/aosp
python -m swirphoneos aosp-plan --workspace /path/to/aosp --jobs 16
python -m swirphoneos aosp-manifest --file /path/to/aosp/swirphoneos-pinned-manifest.xml
python -m swirphoneos build-evidence --workspace /path/to/aosp --manifest /path/to/aosp/swirphoneos-pinned-manifest.xml
python -m swirphoneos cuttlefish-evidence --adb /absolute/path/to/adb > runtime-evidence.json
python -m swirphoneos.cuttlefish_smoke --adb /absolute/path/to/adb > app-smoke-evidence.json
```

The manual self-hosted builder path requires a clean dedicated Linux host, enough RAM/disk and KVM/Cuttlefish support. It intentionally fails closed on local-manifest injection, stale `out/`, unsafe workspace roots and unreviewed `vendor/swir/` files.

### Read-only device and recovery evidence

```sh
python -m swirphoneos inspect-device --transport adb --tool /absolute/path/to/adb > adb-observation.json
python -m swirphoneos inspect-device --transport fastboot --tool /absolute/path/to/fastboot --partitions > fastboot-observation.json
python -m swirphoneos hardware-evidence --adb-report adb-observation.json --fastboot-report fastboot-observation.json > hardware-evidence.json
python -m swirphoneos transaction-plan --file /absolute/path/to/plan.json
python -m swirphoneos transaction-evidence --plan /absolute/path/to/plan.json --artifacts /absolute/path/to/artifacts --journal /absolute/path/to/recovery-journal.json
```

The new SwirRoot readiness binder can then show which root policy gates are still missing without performing a device write:

```sh
python -m swirphoneos.root_readiness_cli \
  --action enable \
  --exact-build '<exact SwirPhoneOS build identity>' \
  --journal /absolute/path/to/recovery-journal.json \
  --hardware /absolute/path/to/hardware-evidence.json
```

With the current repository policy and correlation-only hardware evidence, `transition_ready` remains false by design.

## ✅ Requirements and compatibility

### Host tooling

- Python 3.11+ is the supported host-tooling family tested by CI.
- SwirPhoneStudio has a Windows x64 developer packaging path.
- Physical diagnostics require an explicitly selected trusted Android SDK `adb` or `fastboot` executable.
- AOSP/Cuttlefish builds require a capable dedicated Linux x86-64 builder; normal hosted CI is not treated as build/boot evidence.

### Device compatibility

The first planned physical reference is **OnePlus Nord AC2003 (`avicii`)**, currently **`PLANNED_NOT_SUPPORTED`**. No flashing or root support is enabled for it.

A generic ARM64 GSI target exists for development, but a built GSI is not proof that it is safe on an arbitrary Treble phone. Treble/VTS, vendor interface compatibility, AVB/boot requirements, recovery and per-device functionality must be validated before any support claim.

## 🏗️ Architecture

```text
Linux kernel
   ↓
AOSP / Android-compatible userspace + HAL/vendor integration
   ↓
SwirPhoneOS product, services, design language and system apps
   ├── shared core
   ├── Cuttlefish x86_64 developer product
   ├── ARM64 GSI development target
   └── exact device-specific profiles / ports

PC side
   └── SwirPhoneStudio → read-only diagnostics → recovery/install evidence → future gated execution

Privilege side
   └── SwirRoot → exact-build policy → rollback/journal evidence → future physically validated backend only
```

More detail: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/AOSP_BUILD_WORKSPACE.md`](docs/AOSP_BUILD_WORKSPACE.md), [`docs/HARDWARE_EVIDENCE.md`](docs/HARDWARE_EVIDENCE.md), [`docs/RECOVERY_TRANSACTIONS.md`](docs/RECOVERY_TRANSACTIONS.md), [`docs/SWIRROOT.md`](docs/SWIRROOT.md), [`docs/SWIRROOT_READINESS_EVIDENCE.md`](docs/SWIRROOT_READINESS_EVIDENCE.md).

## 🌍 Localization

English is the canonical fallback/source language. All twenty current Android source apps contain EN, PL, NB, DE, ES, FR, PT and AR catalogs with RTL-aware configuration. Source lint checks key parity, formatter/plural contracts and common hardcoded Java UI sinks.

Runtime locale switching, text expansion, fonts/scripts, accessibility and visual Arabic RTL still require the first real SwirPhoneOS boot and interactive review. First-boot setup, launcher, SystemUI, recovery and every bundled app are expected to use the same shared localization discipline as implementation expands.

## 🔐 Safety and limitations

SwirPhoneOS intentionally prefers a blocked state to an unsafe compatibility claim.

- no generic "works on every Android phone" promise;
- no bootloader exploit, silent unlock or vendor-protection bypass path;
- no unattended flash/erase/relock operation in current tooling;
- no working SwirRoot backend or supported root build;
- no beta until a reproducible OS build, real boot, safe install/rollback/recovery and at least one physically verified phone profile exist;
- telephony, camera, recorder/audio and root status are always stated per exact tested device/build;
- read-only ADB/Fastboot correlation is not cryptographic hardware identity and never authorizes writes.

## 🗺️ Roadmap and releases

The current weighted roadmap remains **2%** and **Beta 0/9**. See [`ROADMAP.md`](ROADMAP.md) and [`BETA_RELEASE_GATE.md`](BETA_RELEASE_GATE.md) for the evidence required before release.

There is **no public SwirPhoneOS beta image today**. A future beta must include real binaries/images, manifest/checksums, exact compatibility matrix, installation/recovery instructions and known issues only after every mandatory gate is satisfied.

## 🗂️ Project structure

```text
platform/          AOSP product, Cuttlefish/GSI integration and bounded staging
system_apps/       machine-readable essential-app registry
swirphoneos/       host safety, build, evidence and diagnostics tooling
swirroot/          SwirRoot policy metadata
studio/            SwirPhoneStudio desktop application
 device_packs/     per-device metadata/ports (unsupported until validated)
docs/              engineering, evidence, i18n and safety documentation
tests/             fail-closed host regression suite
```

## 🔎 Search Keywords

`SwirPhoneOS` • `AOSP Android 17 custom OS` • `Linux mobile operating system` • `Android GSI ARM64` • `Cuttlefish AOSP build` • `SwirPhoneStudio` • `SwirRoot` • `Android device profiles` • `safe Android flashing design` • `Android recovery rollback` • `Treble GSI validation` • `Android system apps` • `Android localization RTL` • `OnePlus Nord avicii port` • `reproducible AOSP build`

<img width="100%" src="https://raw.githubusercontent.com/Swir/Swir/main/assets/power-divider-v4.svg" alt="SWIR electric divider" />

<div align="center">

### `BUILD • VERIFY • RECOVER • EVOLVE`

⭐ **If this project is useful, consider leaving a star.**

[**← SWIR profile**](https://github.com/Swir) · [**All projects →**](https://github.com/Swir?tab=repositories)

**by Swir**

</div>
