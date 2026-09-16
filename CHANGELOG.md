# Changelog

## Unreleased

### SwirNotes, SwirCalendar, composable staging and stronger runtime evidence

Added `SwirNotes` and `SwirCalendar` as meaningful permission-free Android source applications. Notes stores owner-created notes in an app-private SQLite database, supports create/edit/delete/search, explicit text sharing and user-selected Markdown export. Calendar stores a local agenda in app-private SQLite, supports date/time editing and search, and provides explicit sharing plus user-selected iCalendar export. Both include original SwirPhoneOS vector icons, EN/PL/NB/DE/ES/FR/PT/AR resources with RTL support and dependency-free host tests for pure-Java policy cores. CalendarProvider integration remains unimplemented and is explicitly rejected by the current source validator rather than being overclaimed.

AOSP staging now supports strict `stage_manifest.d/*.json` fragments in addition to the primary manifest. Global duplicate source/destination detection, POSIX-relative path validation, the `vendor/swir/` destination boundary, file-count/size bounds and symlink rejection remain fail-closed. This makes independent app additions reviewable without weakening staging safety.

Cuttlefish evidence was strengthened beyond package presence. For each source-ready package the read-only collector now asks Android's package manager to resolve a launcher activity and requires that resolution to stay inside the expected package. It still refuses activity launch, install, package mutation, root, reboot and flash commands and never promotes registry status automatically. The registry is now **9 `ANDROID_SOURCE`, 11 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**. No real AOSP build or boot exists yet, so weighted progress remains **2%** and Beta remains **0/9**.

### SwirClock and Cuttlefish runtime evidence

Added `SwirClock` as the seventh meaningful first-party Android source application. It provides locale-formatted local/UTC time, a foreground stopwatch, a bounded foreground timer and an explicit user-visible hand-off to Android's alarm creation surface. It requests no Android permissions and does not silently create alarms.

Added a strict read-only local Cuttlefish runtime-evidence collector for boot/product/fingerprint/package evidence. No status promotion or device write is performed.

### SwirUpdate and SwirPrivacy Android sources

Added two beta-critical first-party Android sources. `SwirUpdate` exposes local build/channel state and host-tested SHA-256/RSA metadata verification while package download/staging/recovery installation remains disabled. `SwirPrivacy` is a permission-free searchable center backed by an exact reviewed allowlist of Android privacy surfaces.

### SwirFiles and SwirDeviceCare Android sources

Added a user-granted Storage Access Framework file manager source and permission-free device diagnostics backed by real Android framework state.

### SwirSettings source and multi-app Android validation

Added a permission-free settings hub source with localized search, real build/device status, reviewed Android settings routes and multi-app source validation.

### First functional Android application source and bounded source staging

Added `SwirCalculator`, explicit `ANDROID_SOURCE` state and a bounded `platform/aosp_product/stage_manifest.json` allowlist.

### Reproducible AOSP workspace and resolved-manifest evidence

Added exact-tag Repo planning, resolved-manifest SHA validation and explicit local source staging without phone writes.

### Unified SwirPhoneStudio diagnostics and first Cuttlefish product slice

Integrated strict read-only ADB and Fastboot/FastbootD cores into Studio, added the first x86_64 Cuttlefish product source and Windows developer packaging.

### Pinned Android 17 baseline

Pinned the development baseline to official Android 17 release metadata and added a bounded read-only build-host preflight. No source build/boot is claimed.

### Global localization, app registry and SwirRoot safety contracts

Moved Studio localization to validated EN/PL/NB/DE/ES/FR/PT/AR catalogs, defined the complete 20-app suite and added the fail-closed SwirRoot policy. Root writes remain disabled and supported root builds remain zero.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

Added the Python/Tk SwirPhoneStudio foundation, custom icon, read-only ADB/Fastboot diagnostics, strict metadata-only device registry, weighted progress/beta gate accounting, Windows/Linux host CI and initial localization. No Android image or physical-phone support was claimed.

## 0.0.1 — Initial concept archive

The earlier SwirOS planning package was not a bootable OS, installer or hardware-supported release. Its scope continues here with corrected safety and readiness distinctions.
