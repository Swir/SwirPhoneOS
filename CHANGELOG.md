# Changelog

## Unreleased

### First functional Android application source and bounded source staging

Added the first meaningful first-party Android application source to the SwirPhoneOS AOSP product: `SwirCalculator`. It is a permission-free AOSP `android_app` under `org.swir.phoneos.calculator`, includes an original SwirPhoneOS vector icon and dark/cyan UI, and uses a pure-Java BigDecimal engine for basic arithmetic, decimals, sign, percent, backspace and error handling. The engine has a dependency-free host Java test. Android resources cover English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic; the activity follows locale layout direction and exposes accessibility descriptions.

Added an explicit `ANDROID_SOURCE` app-registry state so checked-in Android source cannot be mistaken for `ANDROID_RUNTIME`. SwirCalculator is the first source-ready app; the other 19 essential apps remain `HOST_CONTRACT`, and all runtime/hardware-verified counts remain zero. Scientific math remains a declared target, not an implemented capability.

Replaced fixed two-file product staging with `platform/aosp_product/stage_manifest.json`, an explicit bounded allowlist for product/app source copied only under `vendor/swir/`. Traversal, absolute paths, duplicate source/destination identities, symlink/missing files and oversized source bundles are rejected. Added `python -m swirphoneos android-apps`, source/manifest/localization/staging tests and a CI Java engine smoke. No AOSP build, APK runtime, Cuttlefish boot, GSI or physical-device claim is made; project progress remains **2%** and Beta remains **0/9**.

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
