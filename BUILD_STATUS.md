# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-17**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB / Fastboot | Strict local-USB allowlists implemented; exact firmware/build, verified-boot/slot hints and bounded partition hints can be recorded; no physical USB evidence captured yet |
| Cross-transport hardware evidence | Integrity-hashed ADB+Fastboot correlation and exact transaction/profile/build matching implemented; always `hardware_verified=false`, `write_allowed=false`, `flash_allowed=false`, `root_allowed=false`; no real avicii observation captured yet |
| Device profile registry | Metadata-only schema; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI and Windows developer packaging; no write controls |
| Transaction evidence | Local-only exact install+rollback artifact size/SHA-256 verification and create-only recovery journal implemented; `write_allowed=false`; no device commands |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace | Exact-tag plan, resolved-manifest SHA validation, bounded fragment staging and schema-v5 exact destination-tree closure implemented |
| AOSP build identity | Requires pinned Android release/API, build ID `CP2A.260605.016`, security patch `2026-06-05`, `userdebug`, exact manifest and hashed core images; no real output has passed |
| Dedicated AOSP builder workflow | Manual-only self-hosted sync/stage/build path with optional exact-product Cuttlefish runtime/smoke evidence; no successful AOSP run recorded |
| AOSP failure evidence | Failed runs retain bounded diagnostics and remain `FAILED_NOT_READY`; no promotion/write/root flags can become true |
| Cuttlefish runtime evidence | Exact product/device/manufacturer/API/build-type/fingerprint/package/launcher collector exists; not yet run against a built SwirPhoneOS image |
| Cuttlefish app launch smoke | Exact-identity emulator gate + package-local launch + resumed-activity confirmation implemented for all source-ready apps; not yet exercised against a built image |
| Cuttlefish product | `PRODUCT_PACKAGES` includes all 20 essential first-party apps; **not built or booted** |
| ARM64 GSI product | Source contract registered as `swirphoneos_gsi_arm64-aosp_current-userdebug`; standard AOSP ARM64 + GSI-release inheritance, all 20 apps, exact staging and `systemimage` plan implemented; **not built, Treble/VTS-validated or physically tested** |
| ARM64 GSI build evidence | Manual-only self-hosted workflow and fail-closed `system.img` SHA-256/build-identity collector implemented; compatibility/install/rollback/write/release flags remain false; no successful GSI build evidence recorded |
| Swir Phone | `ANDROID_SOURCE`; permission-free keypad + explicit `ACTION_DIAL`; in-call/default-role/recent calls open |
| Swir Contacts | `ANDROID_SOURCE`; exactly `READ_CONTACTS`, scoped provider browse/search, Android-managed create/edit, vCard import/export; runtime unverified |
| Swir Messages | `ANDROID_SOURCE`; permission-free local compose/draft + explicit `ACTION_SENDTO`/`smsto:`; MMS/history/runtime/carrier behavior open |
| Swir Camera | `ANDROID_SOURCE`; permission-free CameraManager capability reporting + owner-visible photo/video capture hand-off; direct capture and exact-device photo/video remain open |
| Swir Gallery | `ANDROID_SOURCE`; scoped MediaStore browse/search/open/share and owner-confirmed delete; albums open |
| Swir Files | `ANDROID_SOURCE`; user-granted SAF operations; runtime unverified |
| Swir Settings | `ANDROID_SOURCE`; reviewed settings routes/search/device state; runtime unverified |
| Swir Browser | `ANDROID_SOURCE`; exactly `INTERNET`, HTTPS-only WebView with conservative privacy defaults; downloads open |
| Swir Clock | `ANDROID_SOURCE`; localized time/stopwatch/timer/user-visible alarm hand-off |
| Swir Calculator | `ANDROID_SOURCE`; basic math host-tested; scientific math open |
| Swir Notes | `ANDROID_SOURCE`; local SQLite CRUD/search/share/Markdown export |
| Swir Recorder | `ANDROID_SOURCE`; exactly `RECORD_AUDIO`, foreground-only private AAC/MPEG-4 capture/playback/export; exact-device audio unverified |
| Swir Calendar | `ANDROID_SOURCE`; local agenda/share/ICS export; CalendarProvider bridge open |
| Swir Weather | `ANDROID_SOURCE`; exactly `INTERNET`, bounded Open-Meteo HTTPS forecast for owner-entered coordinates, unit preference/provider attribution; no location permission |
| Swir Update | `ANDROID_SOURCE`; read-only state + SHA-256/RSA metadata verification; install path disabled |
| Swir Backup | `ANDROID_SOURCE`; permission-free owner-selected bounded archive creation + build recovery metadata + safe archive inspection; restore orchestration open |
| Swir Privacy | `ANDROID_SOURCE`; reviewed privacy routes; live indicators/history open |
| Swir Device Care | `ANDROID_SOURCE`; permission-free framework diagnostics; exact-device interpretation unverified |
| Swir Apps | `ANDROID_SOURCE`; permission-free local launcher catalog + signer SHA-256 provenance; remote catalog/install/update status open |
| SwirRoot | `ANDROID_SOURCE`; localized owner UI + non-exported status/diagnostic service + host-tested gates; mutation backend hard-disabled, supported builds = 0, state = `UNAVAILABLE` |
| Android source safety | Exact per-app permission allowlists; process/broad-storage primitives rejected; network primitives allowed only for reviewed Browser/Weather source; SwirRoot has additional no-mutation gates |
| Android source localization | All 20 source-ready apps have EN/PL/NB/DE/ES/FR/PT/AR catalogs; key/formatter/plural/UI-literal lint passes source contracts; runtime locale/RTL behavior unverified |
| Source capability accounting | Schema v3 tracks missing capabilities per app, including camera capture, browser downloads, backup restore, telephony gaps and SwirRoot guided transitions |
| System apps | 20-app registry: **20 `ANDROID_SOURCE`, 0 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified** |
| SwirRoot host policy | `write_operations_enabled=false`; supported root builds = 0; exploit/bypass methods forbidden |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/Cuttlefish image | Not built |
| ARM64 GSI image | Not built; source/plan/evidence tooling exists, but `gsi_validation` remains incomplete |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated; no real evidence set captured/reviewed |
| Backup/install/recovery/stock restore | Evidence foundations and source-stage document backup exist; no verified partition map, write engine, restore orchestration or physical restore test |
| Signing/OTA | Verification primitives/source contracts only; release signing/update/rollback runtime path not implemented |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, evidence rejection logic, desktop packaging, exact staging-tree closure, read-only hardware correlation, local transaction safety, Cuttlefish smoke parsing, Android source localization, exact permission allowlists, ARM64 GSI source/build-evidence contracts and pure-Java policies for the complete 20-app source suite. It cannot establish Android runtime compatibility, Treble/VTS compliance, telephony/carrier delivery, direct camera capture, working root, recovery safety or hardware support. AOSP/platform credit remains blocked until the pinned source synchronizes and builds; emulator credit remains blocked until that exact image boots and reviewed runtime plus app-smoke evidence is recorded; GSI credit remains blocked until a real ARM64 image builds and relevant Treble/VTS plus compatibility evidence exists. Completing source breadth or host-only GSI tooling grants no weighted milestone credit.