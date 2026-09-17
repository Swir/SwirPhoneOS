# Changelog

## Unreleased

### Fail-closed install/rollback transaction evidence

Added `swirphoneos.transaction_evidence`, a local-only preparation layer for future device-specific installation and recovery work. Schema v1 binds one transaction to an exact device profile/current-build/target-build tuple, requires both install and rollback artifact sets, verifies exact byte sizes and SHA-256 digests, rejects traversal/symlink/duplicate-key/unknown-field inputs, and can persist a create-only fsynced JSON journal. The journal remains explicitly `ARTIFACTS_VERIFIED_READ_ONLY`, records `owner_confirmation_recorded=false`, and can never set `write_allowed=true`.

Added `transaction-plan` and `transaction-evidence` CLI surfaces plus negative/positive unit coverage for canonical plan hashing, mandatory rollback/owner gates, artifact tamper detection, path confinement, symlink rejection, cross-plan evidence rejection and no-overwrite journaling. Added `docs/RECOVERY_TRANSACTIONS.md` to define the evidence chain required before any future physical write path. This is real install/restore infrastructure work, but it does not complete the milestone: no partition map, supported hardware, write engine or physical install/restore proof exists. Weighted progress therefore remains **2%** and Beta remains **0/9**.

### SwirRoot Android source-stage control surface

Added `SwirRoot` as the tenth meaningful first-party Android source application. It now has an original localized owner UI, current-build fingerprint diagnostics, explicit owner-confirmed enable/unroot review dialogs, a non-exported bound status service, a bounded app-private workflow-review audit, an original SwirPhoneOS icon and EN/PL/NB/DE/ES/FR/PT/AR resources with RTL support.

Added a dependency-free pure-Java `RootPolicy` and host test for the exact-build/profile/owner/rollback/journal/update-state/expected-non-root gates. The Android service remains deliberately fail-closed: `WRITE_BACKEND_ENABLED=false`, `SUPPORTED_BUILD=false`, current state is `UNAVAILABLE`, and no process execution, `su`, boot-image mutation, partition write, unlock, flash or exploit/bypass path exists. `root_state` and `authorization_audit` are source-implemented; `guided_enable` and `guided_unroot` remain future capabilities requiring a legitimate exact-build backend plus physical rollback/unroot/recovery evidence.

Strengthened Android source validation so forbidden process/network/storage primitives are checked across **all production Java files**, not only the primary activity and policy files. SwirRoot receives additional checks for hard-disabled mutation support and the mandatory safety gate model. Host CI now compiles and executes the pure-Java SwirRoot transition-policy test. The registry is **10 `ANDROID_SOURCE`, 10 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**. No AOSP build/boot or physical root claim is made, so weighted progress remains **2%** and Beta remains **0/9**.

### Exact-build Cuttlefish launch and emulator-only app smoke

Extended the manual self-hosted AOSP evidence workflow so runtime collection no longer depends on a separately pre-launched guest. After the exact pinned product builds, the workflow can source that product environment, launch it with `launch_cvd --daemon --report_anonymous_usage_stats=n`, poll the strict schema-v3 runtime collector until verified boot is complete, collect build/runtime fingerprint continuity, and always attempt `stop_cvd` cleanup under an isolated workflow HOME.

Added `swirphoneos.cuttlefish_smoke`, an emulator-only launch-smoke runner for every source-ready application. It first requires complete exact-identity SwirPhoneOS Cuttlefish evidence, then launches only the resolved package-local launcher component through a narrow `am start -W -n` allowlist and confirms the expected package as the resumed foreground activity. Physical/network transports, arbitrary shell, install/uninstall, root, reboot, flash, erase and settings mutation remain rejected. The report explicitly records the transient foreground-state mutation and never auto-promotes registry status.

Added unit coverage for successful/failed `am start -W` parsing, foreground confirmation, physical/persistent-mutation rejection and the complete source-ready app exercise path. Documentation treats `app-smoke-evidence.json` as an additional runtime review artifact. No real AOSP build/boot has completed yet, so weighted progress remains **2%** and Beta remains **0/9**.

### AOSP build provenance and exact runtime identity binding

Added fail-closed `build-evidence` tooling that binds a completed local AOSP output to the fully pinned `repo manifest -r`, hashes reviewed core product artifacts, and extracts the exact build fingerprint/build ID/release/API/build type from the produced system properties. Added `evidence-bundle` so a complete Cuttlefish report is accepted only when its runtime fingerprint exactly matches the fingerprint from the hashed build output. The canonical bundle receives its own SHA-256 and never auto-promotes registry state.

Cuttlefish evidence schema v3 now requires the exact SwirPhoneOS product, `vsoc_x86_64_only` device identity, `Swir` manufacturer, Android 17 / API 37, `userdebug`, build ID/fingerprint, all source-ready packages and package-local launcher resolution. Added negative tests for API drift, missing artifacts, fingerprint mismatch and duplicate-key evidence JSON.

Added a manual-only `aosp-build-evidence.yml` workflow for a dedicated self-hosted `swir-aosp-builder`. It performs exact-tag init/sync, resolved-manifest capture, reviewed source staging, the real Cuttlefish product build and build-evidence capture. No successful AOSP build/boot is claimed yet, so weighted progress remains **2%** and Beta remains **0/9**.

### SwirNotes, SwirCalendar, composable staging and stronger runtime evidence

Added `SwirNotes` and `SwirCalendar` as meaningful permission-free Android source applications. Notes stores owner-created notes in an app-private SQLite database, supports create/edit/delete/search, explicit text sharing and user-selected Markdown export. Calendar stores a local agenda in app-private SQLite, supports date/time editing and search, and provides explicit sharing plus user-selected iCalendar export. Both include original SwirPhoneOS vector icons, EN/PL/NB/DE/ES/FR/PT/AR resources with RTL support and dependency-free host tests for pure-Java policy cores. CalendarProvider integration remains unimplemented and is explicitly rejected by the current source validator rather than being overclaimed.

AOSP staging now supports strict `stage_manifest.d/*.json` fragments in addition to the primary manifest. Global duplicate source/destination detection, POSIX-relative path validation, the `vendor/swir/` destination boundary, file-count/size bounds and symlink rejection remain fail-closed. This makes independent app additions reviewable without weakening staging safety.

Cuttlefish evidence was strengthened beyond package presence. For each source-ready package the read-only collector asks Android's package manager to resolve a launcher activity and requires that resolution to stay inside the expected package. It still refuses install, package mutation, root, reboot and flash commands and never promotes registry status automatically.

### SwirClock and Cuttlefish runtime evidence

Added `SwirClock` as a meaningful first-party Android source application. It provides locale-formatted local/UTC time, a foreground stopwatch, a bounded foreground timer and an explicit user-visible hand-off to Android's alarm creation surface. It requests no Android permissions and does not silently create alarms.

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
