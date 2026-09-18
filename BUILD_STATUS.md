# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-18**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB / Fastboot | Strict local-USB allowlists implemented; exact firmware/build, verified-boot/slot hints and bounded partition hints can be recorded; no physical USB evidence captured yet |
| Cross-transport hardware evidence | Integrity-hashed ADB+Fastboot correlation and exact transaction/profile/build matching implemented; always `hardware_verified=false`, `write_allowed=false`, `flash_allowed=false`, `root_allowed=false`; no real avicii observation captured yet |
| Device profile registry | Schema v1 is strictly metadata-only: symlink/duplicate-key/path-id drift rejected and verified status/partition map/build/recovery claims forbidden; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| Device support readiness | Exact profile-byte SHA-256 + read-only hardware evidence + recovery-journal binding implemented; schema v1 always keeps physical/install/rollback/runtime gates false, capabilities `UNVERIFIED`, support/install/write/root/promotion denied |
| Physical device validation | Schema v2 host-only binder ties all seven physical support gates plus telephony/camera/audio/Wi-Fi/Bluetooth/sensors/GNSS/NFC review to distinct local size/SHA-256 evidence under exact profile/current-build/target-build readiness; candidate review never authorizes support, profile promotion, install, writes or root; no real avicii bundle exists |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI, strict local SwirRoot-readiness evidence review and Windows developer packaging; no write/root controls |
| Studio readiness evidence | Absolute regular JSON only; duplicate-key/symlink/oversize/integrity/forged-write rejection; UI summary remains `transition_ready=false`, `device_write_allowed=false` under the current readiness schema |
| Host localization | Shared EN/PL/NB/DE/ES/FR/PT/AR catalog with strict complete-locale data fragments; current Studio readiness surface is fully translated in all eight host locales |
| Transaction evidence | Local-only exact install+rollback artifact size/SHA-256 verification and create-only recovery journal implemented; `write_allowed=false`; no device commands |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace | Exact-tag plan, resolved-manifest SHA validation, bounded fragment staging and schema-v5 exact destination-tree closure implemented |
| AOSP build identity | Requires pinned Android release/API, build ID `CP2A.260605.016`, security patch `2026-06-05`, `userdebug`, exact manifest and hashed core images; no real output has passed |
| Dedicated AOSP builder workflow | Manual-only self-hosted sync/stage/build path with optional exact-product Cuttlefish boot, all-app launch smoke, full EN/PL/NB/DE/ES/FR/PT/AR locale matrix, runtime-review binding and exact-adb byte-continuity trust; no successful AOSP run recorded |
| AOSP failure evidence | Failed runs retain bounded diagnostics including locale/review/trust phases and remain `FAILED_NOT_READY`; no promotion/write/root flags can become true |
| Cuttlefish runtime evidence | Exact product/device/manufacturer/API/build-type/fingerprint/package/launcher collector exists; not yet run against a built SwirPhoneOS image |
| Cuttlefish app launch smoke | Exact-identity emulator gate + package-local launch + resumed-activity confirmation implemented for all source-ready apps; not yet exercised against a built image |
| Cuttlefish runtime localization review | All 20 source-ready apps × all 8 checked-in locales can be exercised with exact restoration; boot/launch/locale review is bound to the same app manifest/build fingerprint and exact-adb trust window; visual RTL/accessibility/translation quality remain explicitly unverified; no real runtime report exists |
| Cuttlefish product | `PRODUCT_PACKAGES` includes all 20 essential first-party apps; **not built or booted** |
| ARM64 GSI product | Source contract registered as `swirphoneos_gsi_arm64-aosp_current-userdebug`; standard AOSP ARM64 + GSI-release inheritance, all 20 apps, exact staging and `systemimage` plan implemented; **not built, Treble/VTS-validated or physically tested** |
| ARM64 GSI build evidence | Manual-only self-hosted workflow and fail-closed `system.img` SHA-256/build-identity collector implemented; compatibility/install/rollback/write/release flags remain false; no successful GSI build evidence recorded |
| Shared Swir Android design | `SwirDesign` source contract v4 is statically linked and `Theme.SwirPhoneOS` declared by all 20 system apps; eight activities directly consume the shared palette/touch tokens, including all 5/5 beta-critical core apps; Android build, visual/runtime and accessibility review remain unverified |
| Swir Phone | `ANDROID_SOURCE`; permission-free keypad + explicit `ACTION_DIAL`; in-call/default-role/recent calls open |
| Swir Contacts | `ANDROID_SOURCE`; exactly `READ_CONTACTS`, scoped provider browse/search, Android-managed create/edit, vCard import/export; runtime unverified |
| Swir Messages | `ANDROID_SOURCE`; permission-free local compose/draft + explicit `ACTION_SENDTO`/`smsto:`; MMS/history/runtime/carrier behavior open |
| Swir Camera | `ANDROID_SOURCE`; permission-free CameraManager capability reporting + owner-visible photo/video capture hand-off; direct capture and exact-device photo/video remain open |
| Swir Gallery | `ANDROID_SOURCE`; scoped MediaStore browse/search/open/share and owner-confirmed delete; albums open |
| Swir Files | `ANDROID_SOURCE`; user-granted SAF browse/search/copy/move/rename/create/share/delete flows; shared Swir design/touch tokens at source stage; provider/runtime/accessibility behavior unverified |
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
| SwirRoot readiness | Recovery journal + correlated read-only hardware evidence + exact target build binding implemented; current schema cannot authorize root and always keeps transition/write/promotion false |
| Android source safety | Exact per-app permission allowlists; process/broad-storage primitives rejected; network primitives allowed only for reviewed Browser/Weather source; SwirRoot has additional no-mutation gates |
| Android source localization | All 20 source-ready apps have EN/PL/NB/DE/ES/FR/PT/AR catalogs; key/formatter/plural/UI-literal lint passes source contracts; automated Cuttlefish package×locale switching/restoration is wired into the trusted runtime workflow but has not run; visual RTL/accessibility quality remains unverified |
| Source capability accounting | Schema v3 tracks missing capabilities per app, including camera capture, browser downloads, backup restore, telephony gaps and SwirRoot guided transitions |
| System apps | 20-app registry: **20 `ANDROID_SOURCE`, 0 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified** |
| SwirRoot host policy | `write_operations_enabled=false`; supported root builds = 0; exploit/bypass methods forbidden |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/Cuttlefish image | Not built |
| ARM64 GSI image | Not built; source/plan/evidence tooling exists, but `gsi_validation` remains incomplete |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated; readiness and physical-validation tooling can package future exact-device evidence for review, but no real partition-map/restore/boot/install/rollback/capability evidence set has been captured |
| Backup/install/recovery/stock restore | Evidence foundations and source-stage document backup exist; no verified partition map, write engine, restore orchestration or physical restore test |
| Signing/OTA | Verification primitives/source contracts only; release signing/update/rollback runtime path not implemented |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, evidence rejection logic, desktop packaging, exact staging-tree closure, read-only hardware correlation, local transaction safety, metadata-profile hardening, preparation-only device-support readiness, file-backed physical-validation binding, Cuttlefish smoke/localization parsers and evidence binders, Android source localization, exact permission allowlists, ARM64 GSI source/build-evidence contracts, shared Android design source integration, shared host-localization fragments and pure-Java policies for the complete 20-app source suite. It cannot establish Android runtime compatibility, rendered visual quality, accessibility, Treble/VTS compliance, telephony/carrier delivery, direct camera capture, working root, recovery safety or hardware support. A complete host-validated physical bundle is still only a review input; checked-in profile promotion and beta/release credit require audited real-device outcomes and a separate reviewed support policy. AOSP/platform credit remains blocked until the pinned source synchronizes and builds; emulator credit remains blocked until that exact image boots and the full trusted boot/launch/locale review chain is recorded; GSI credit remains blocked until a real ARM64 image builds and relevant Treble/VTS plus compatibility evidence exists. Completing source breadth, shared design integration, host-only Studio/readiness integration, physical-evidence packaging or host-only GSI tooling grants no weighted milestone credit.
