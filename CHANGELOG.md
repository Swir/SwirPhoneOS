# Changelog

## Unreleased

### Source-ready Swir Phone dialer

Added `SwirPhone` as meaningful first-party Android source with an original dark/cyan keypad, dedicated icon, accessibility labels and EN/PL/NB/DE/ES/FR/PT/AR resources. A dependency-free `DialerPolicy` is host-tested for bounded fail-closed normalization, keypad append/erase behavior and malformed input rejection. The app is permission-free and uses the user-visible `Intent.ACTION_DIAL` hand-off rather than `CALL_PHONE` or a direct Telecom call path.

Extended Android source validation with an exact Swir Phone source contract that rejects direct-call permission/path drift, preserves complete staging, and tracks `dialer` as implemented while leaving `phone:in_call` and `phone:recent_calls` explicitly unfinished. The Cuttlefish product and exact source staging now include Swir Phone. CI runs the pure-Java dial policy in both the main Linux/Python 3.14 path and a focused source check. Registry state is **15 `ANDROID_SOURCE`, 5 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**.

This is source-level communication-app progress only. It does not claim a default-dialer role, working in-call UI, call history, modem/IMS/telephony compatibility, AOSP build/boot or physical-device verification. Weighted progress therefore remains **2%**, 1/10 milestones, and Beta remains **0/9**.

### Swir Contacts, local Software Center and per-app capability accounting

Added `SwirContacts` as meaningful Android source. It requests exactly `READ_CONTACTS`, browses/searches the local Android ContactsProvider, delegates create/edit to Android's authoritative contact UI, provides explicit user-selected vCard import hand-off and exports a selected provider vCard only to a user-selected document. It does not request `WRITE_CONTACTS`, storage or network access. A dependency-free `ContactPolicy` is host-tested for search, provider lookup-key validation and safe export naming.

Added `SwirApps` as a permission-free local Software Center foundation. It enumerates visible launchable applications with PackageManager, exposes package/version information and bounded signing-certificate SHA-256 provenance, launches selected apps and opens Android's authoritative app-details screen. No remote catalog, download or install path exists; `update_status` remains explicitly unfinished. Both new apps include original SwirPhoneOS icons, EN/PL/NB/DE/ES/FR/PT/AR resources, RTL-aware configuration, reviewed AOSP staging and Cuttlefish product integration.

Upgraded Android source reporting to schema v3 with per-app missing capability tracking. Shared capability names can no longer hide another app's unfinished work: Contacts implements its provider bridge while `calendar:provider_bridge` stays open, and `apps:update_status` stays open. CI compiles and executes both new pure-Java policy tests on Linux/Python 3.14. Registry state is now **14 `ANDROID_SOURCE`, 6 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**. This is source-level progress only; no AOSP build/boot or physical-device claim is made, so weighted progress remains **2%** and Beta remains **0/9**.

### Exact AOSP staging-tree closure

Hardened the persistent self-hosted AOSP build path against stale or unreviewed files under `vendor/swir/`. `stage-product` schema v5 now inventories the complete regular-file destination tree before copying and fails closed if a file from an older revision or any other unreviewed source remains outside the current staging manifest. It deliberately does not auto-delete stale files. After copying, the exact destination set must equal the reviewed manifest and the report records pre-existing/current file counts plus `destination_tree_closed=true`.

Extended post-build staged-source evidence to independently re-inventory the full `vendor/swir/` file set after Kati/Soong. A changed/missing staged file, symlink substitution, generated extra file or stale source now blocks build provenance even when all originally listed files still hash correctly. `aosp-run-evidence` and the manual builder workflow require the new schema-v5 closure proof before accepting a build chain. Added cross-platform regression tests for stale pre-build files, post-build extras, closure/count tampering and workflow schema drift, and refreshed AOSP operator documentation.

This is reproducibility/supply-chain hardening only. No Android build, Cuttlefish boot, physical-device support, phone write, root path or release gate is claimed, so weighted progress remains **2%** and Beta remains **0/9**.

### Scoped Swir Gallery and foreground Swir Recorder Android sources

Added `SwirGallery` as meaningful Android source using the least-privilege `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO` permissions. It browses granted local photos/videos through MediaStore, supports local search, opens and shares URI-granted media, and delegates deletion to Android's owner-confirmed `MediaStore.createDeleteRequest` flow. It does not request broad storage access or direct media-write privileges. Album grouping remains an explicit future capability.

Added `SwirRecorder` as meaningful foreground-only Android source using exactly `RECORD_AUDIO`. It records AAC audio in an MPEG-4 container to app-private storage, supports pause/resume/stop and local playback, exposes framework microphone mute state, requires confirmation for local deletion and exports only through a user-selected `ACTION_CREATE_DOCUMENT` destination. Active recording is deliberately stopped when the activity leaves the foreground; no background recording service exists in this source stage. Exact-device microphone/audio behavior remains unverified.

Refactored Android source validation from a blanket zero-permission rule to exact per-app permission allowlists while retaining global rejection of network, broad-storage and process-execution primitives. Permission-free apps remain permission-free. Gallery and Recorder gained pure-Java policy host tests, original SwirPhoneOS icons, EN/PL/NB/DE/ES/FR/PT/AR resources with RTL, AOSP product/staging integration and CI compilation. The registry became **12 `ANDROID_SOURCE`, 8 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified**. No AOSP build/boot or physical audio/media verification was claimed, so weighted progress remained **2%** and Beta **0/9**.

### Complete AOSP run evidence chain and exact builder gate

Fixed a fail-closed orchestration defect in the manual self-hosted AOSP workflow: `build-preflight` emits mandatory checks as `checks[].id` / `checks[].passed`, while the workflow had been reading non-existent `name` / `ok` fields. The builder gate now consumes the actual schema, rejects missing check inventories and also rejects an internally inconsistent report before `repo init` / `repo sync`.

Strengthened `build-evidence` so a completed product is accepted only when its `system/build.prop` matches the pinned Android baseline for release, API level, build ID, security patch level and `userdebug` build type. Added `swirphoneos.aosp_run_evidence` plus the `aosp-run-evidence` CLI surface to bind one exact workflow source commit to builder preflight, AOSP plan, resolved manifest, pre-build staging, post-build staged-source re-verification and hashed build output. Optional Cuttlefish runtime, app-launch smoke and build/runtime bundle evidence is all-or-nothing and must use the same exact fingerprint/package set.

The workflow now emits `aosp-run-evidence.json` after a successful build chain and includes it with the immutable evidence artifact set. Regression coverage rejects build-ID/security-patch drift, preflight schema drift, cross-run stage hashes, runtime/smoke package mismatch, partial runtime groups, duplicate JSON keys and mixed build/runtime bundles. No real AOSP build or boot is claimed by these host-side changes, so weighted progress remains **2%** and Beta remains **0/9**.

### Cross-transport read-only hardware evidence

Expanded the physical-device diagnostics path without adding any write capability. ADB observations include exact build fingerprint, board/hardware, slot and verified-boot/VBMeta state hints. Fastboot can optionally query only bounded `has-slot:<partition>` and `partition-size:<partition>` variables for a reviewed partition-name allowlist; `getvar all` and every mutating Fastboot command remain unavailable.

Added `swirphoneos.hardware_evidence` plus the `hardware-evidence` and `transaction-device-check` CLI commands. Saved ADB and Fastboot unified reports can be correlated only when they resolve to the same local metadata profile, model/codename agree, an exact ADB firmware fingerprint exists, and reported slot/bootloader state does not conflict. The result is integrity-hashed but explicitly remains `CORRELATED_READ_ONLY_NOT_VERIFIED`, with hardware verification, SwirPhoneOS support, writes, flashing and root all false. A transaction plan may be matched against that exact observed profile/model/codename/build fingerprint, but the match remains preparation-only and cannot enable installation.

Added fail-closed tests for evidence tampering, duplicate JSON keys, missing firmware fingerprint, cross-transport slot mismatch and transaction fingerprint mismatch, plus operator documentation in `docs/HARDWARE_EVIDENCE.md`. The `oneplus/avicii` profile remains `PLANNED_NOT_SUPPORTED`; no real device observation or physical restore proof is claimed. Weighted progress therefore remains **2%** and Beta remains **0/9**.

### Fail-closed install/rollback transaction evidence

Added `swirphoneos.transaction_evidence`, a local-only preparation layer for future device-specific installation and recovery work. Schema v1 binds one transaction to an exact device profile/current-build/target-build tuple, requires both install and rollback artifact sets, verifies exact byte sizes and SHA-256 digests, rejects traversal/symlink/duplicate-key/unknown-field inputs, and can persist a create-only fsynced JSON journal. The journal remains explicitly `ARTIFACTS_VERIFIED_READ_ONLY`, records `owner_confirmation_recorded=false`, and can never set `write_allowed=true`.

Added `transaction-plan` and `transaction-evidence` CLI surfaces plus negative/positive unit coverage for canonical plan hashing, mandatory rollback/owner gates, artifact tamper detection, path confinement, symlink rejection, cross-plan evidence rejection and no-overwrite journaling. Added `docs/RECOVERY_TRANSACTIONS.md` to define the evidence chain required before any future physical write path. This is real install/restore infrastructure work, but it does not complete the milestone: no partition map, supported hardware, write engine or physical install/restore proof exists. Weighted progress therefore remains **2%** and Beta remains **0/9**.

### SwirRoot Android source-stage control surface

Added `SwirRoot` as meaningful first-party Android source. It has an original localized owner UI, current-build fingerprint diagnostics, explicit owner-confirmed enable/unroot review dialogs, a non-exported bound status service, a bounded app-private workflow-review audit, an original SwirPhoneOS icon and EN/PL/NB/DE/ES/FR/PT/AR resources with RTL support.

Added a dependency-free pure-Java `RootPolicy` and host test for exact-build/profile/owner/rollback/journal/update-state/expected-non-root gates. The Android service remains deliberately fail-closed: `WRITE_BACKEND_ENABLED=false`, `SUPPORTED_BUILD=false`, current state is `UNAVAILABLE`, and no process execution, `su`, boot-image mutation, partition write, unlock, flash or exploit/bypass path exists. `root_state` and `authorization_audit` are source-implemented; `guided_enable` and `guided_unroot` remain future capabilities requiring a legitimate exact-build backend plus physical rollback/unroot/recovery evidence.

Strengthened Android source validation so forbidden process/network/storage primitives are checked across all production Java files, not only primary activities/policies. SwirRoot receives additional checks for hard-disabled mutation support and the mandatory safety gate model. Host CI compiles and executes the pure-Java SwirRoot transition-policy test. No AOSP build/boot or physical root claim was made.

### Exact-build Cuttlefish launch and emulator-only app smoke

Extended the manual self-hosted AOSP evidence workflow so runtime collection no longer depends on a separately pre-launched guest. After the exact pinned product builds, the workflow can source that product environment, launch it with `launch_cvd --daemon --report_anonymous_usage_stats=n`, poll the strict runtime collector until verified boot is complete, collect build/runtime fingerprint continuity, and always attempt `stop_cvd` cleanup under an isolated workflow HOME.

Added `swirphoneos.cuttlefish_smoke`, an emulator-only launch-smoke runner for every source-ready application. It first requires complete exact-identity SwirPhoneOS Cuttlefish evidence, then launches only the resolved package-local launcher component through a narrow `am start -W -n` allowlist and confirms the expected package as the resumed foreground activity. Physical/network transports, arbitrary shell, install/uninstall, root, reboot, flash, erase and settings mutation remain rejected. The report explicitly records the transient foreground-state mutation and never auto-promotes registry status.

### AOSP build provenance and exact runtime identity binding

Added fail-closed `build-evidence` tooling that binds a completed local AOSP output to the fully pinned `repo manifest -r`, hashes reviewed core product artifacts, and extracts exact build fingerprint/build ID/release/API/build type from produced system properties. Added `evidence-bundle` so complete Cuttlefish evidence is accepted only when runtime fingerprint exactly matches the fingerprint from hashed build output. No successful AOSP build/boot is claimed yet, so weighted progress remains **2%** and Beta remains **0/9**.

### SwirNotes, SwirCalendar, composable staging and stronger runtime evidence

Added `SwirNotes` and `SwirCalendar` as meaningful permission-free Android source applications. Notes stores owner-created notes in an app-private SQLite database with create/edit/delete/search, explicit text sharing and user-selected Markdown export. Calendar stores a local agenda, supports date/time editing/search, sharing and iCalendar export. Both include original icons, EN/PL/NB/DE/ES/FR/PT/AR resources with RTL support and dependency-free host tests. CalendarProvider integration remains explicitly unclaimed.

AOSP staging gained strict `stage_manifest.d/*.json` fragments while retaining global duplicate source/destination detection, POSIX-relative path validation, the `vendor/swir/` boundary, file-count/size limits and symlink rejection.

### SwirClock and Cuttlefish runtime evidence

Added `SwirClock` as a meaningful first-party Android source application with locale-formatted time/date, foreground stopwatch/timer and explicit owner-visible hand-off to Android alarm creation. Added a strict read-only local Cuttlefish runtime-evidence collector for boot/product/fingerprint/package evidence.

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
