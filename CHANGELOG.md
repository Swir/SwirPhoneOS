# Changelog

## Unreleased

### SwirFiles and SwirDeviceCare Android sources

Added two more beta-critical first-party Android source applications. `SwirFiles` uses Android's user-granted Storage Access Framework rather than broad storage permissions: it can persist an explicitly selected tree grant, browse and search that tree, create folders, rename/copy/move/delete where the storage provider advertises support, and open/share granted documents. Deletion requires explicit confirmation. A pure-Java `FilePolicy` validates names and search behavior in host CI.

Added `SwirDeviceCare` as a permission-free diagnostics dashboard backed by real Android framework state for device/security-patch identity, battery and charging, storage, memory and thermal condition. A pure-Java `HealthModel` is host-tested. Both apps have original SwirPhoneOS icons/UI, EN/PL/NB/DE/ES/FR/PT/AR resources with RTL-aware layout, explicit AOSP staging and `PRODUCT_PACKAGES` integration. Source validation now rejects broad storage primitives, missing SAF controls, placeholder Device Care state, localization drift and incomplete staging. The registry is now **4 `ANDROID_SOURCE`, 16 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**. No AOSP build/runtime claim is made; weighted progress remains **2%** and Beta remains **0/9**.

### SwirSettings source and multi-app Android validation

Added `SwirSettings` as the second meaningful first-party Android application source and the first beta-critical app to reach `ANDROID_SOURCE`. It is a permission-free AOSP `android_app` under `org.swir.phoneos.settings` with an original SwirPhoneOS icon and dark/cyan interface, searchable categories, real build/device summary and direct hand-off to reviewed authoritative Android settings pages for Wi-Fi, Bluetooth, display, sound, security, privacy, accessibility, language/region, storage and apps. It never mutates settings itself and requests no Android permissions.

Added Android resources for English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic with RTL-aware layout. The route catalog is pure Java and dependency-free host tested. The source validator is now multi-app aware: every `ANDROID_SOURCE` entry requires a reviewed source contract, full product inclusion/staging, package identity, permission-free source slice, localization parity and explicit implementation evidence. It also rejects duplicate staging destinations and unreviewed Settings actions. The system-app registry was **2 `ANDROID_SOURCE`, 18 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified`** at this step. No Android build/runtime claim was made.

### First functional Android application source and bounded source staging

Added the first meaningful first-party Android application source to the SwirPhoneOS AOSP product: `SwirCalculator`. It is a permission-free AOSP `android_app` under `org.swir.phoneos.calculator`, includes an original SwirPhoneOS vector icon and dark/cyan UI, and uses a pure-Java BigDecimal engine for basic arithmetic, decimals, sign, percent, backspace and error handling. The engine has a dependency-free host Java test. Android resources cover English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic; the activity follows locale layout direction and exposes accessibility descriptions.

Added an explicit `ANDROID_SOURCE` app-registry state so checked-in Android source cannot be mistaken for `ANDROID_RUNTIME`. SwirCalculator was the first source-ready app; runtime/hardware states still require actual Android evidence. Scientific math remains a declared target, not an implemented capability.

Replaced fixed two-file product staging with `platform/aosp_product/stage_manifest.json`, an explicit bounded allowlist for product/app source copied only under `vendor/swir/`. Traversal, absolute paths, duplicate source/destination identities, symlink/missing files and oversized source bundles are rejected. Added `python -m swirphoneos android-apps`, source/manifest/localization/staging tests and CI Java engine smoke. No AOSP build, APK runtime, Cuttlefish boot, GSI or physical-device claim is made.

### Reproducible AOSP workspace and resolved-manifest evidence

Added a fail-closed AOSP workspace contract around the pinned Android 17 baseline. `aosp-plan` emits an exact-tag Repo init/sync, resolved-manifest capture, staging and Cuttlefish build plan without executing it. `aosp-manifest` requires full project SHA revisions and reports SHA-256 evidence. Staging remains an explicit local operation and never talks to a phone.

### Unified SwirPhoneStudio diagnostics and first Cuttlefish product slice

Integrated strict read-only ADB and Fastboot/FastbootD cores into a single Studio workflow with metadata-only profile hints. Added the first x86_64 Cuttlefish product source and Windows developer packaging. Hints remain non-authoritative and no write control is enabled.

### Pinned Android 17 baseline

Pinned the development baseline to official Android 17 release metadata, added a bounded read-only build-host preflight and reproducible platform contracts. No source build/boot is claimed.

### Global localization, app registry and SwirRoot safety contracts

Moved Studio localization to validated data catalogs (EN/PL/NB/DE/ES/FR/PT/AR), defined the complete 20-app suite and added the fail-closed SwirRoot policy. Root writes remain disabled and supported root builds remain zero.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

Added the Python/Tk SwirPhoneStudio foundation, custom icon, read-only ADB/Fastboot diagnostics, strict metadata-only device registry, weighted progress/beta gate accounting, Windows/Linux host CI and initial localization. No Android image or physical-phone support was claimed.

## 0.0.1 — Initial concept archive

The earlier SwirOS planning package was not a bootable OS, installer or hardware-supported release. Its scope continues here with corrected safety and readiness distinctions.
