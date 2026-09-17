# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-17**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB / Fastboot | Strict local-USB allowlists implemented; ADB records exact firmware/build + verified-boot/slot hints and Fastboot optionally records bounded partition size/slot hints; no physical USB evidence captured yet |
| Cross-transport hardware evidence | Integrity-hashed ADB+Fastboot correlation and exact transaction/profile/build matching implemented; always `hardware_verified=false`, `write_allowed=false`, `flash_allowed=false`, `root_allowed=false`; no real avicii observation captured yet |
| Device profile registry | Metadata-only schema; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI and Windows developer packaging; no write controls |
| Transaction evidence | Local-only schema-v1 plan validation, exact install+rollback artifact size/SHA-256 verification and create-only fsynced recovery journal implemented; `write_allowed=false`, owner confirmation not recorded, no device commands |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace | Exact-tag plan, resolved-manifest SHA validation, bounded manifest/fragment staging and fail-closed build-artifact provenance tooling implemented; schema-v5 staging rejects stale/unreviewed `vendor/swir` files and proves exact destination-file closure |
| AOSP build identity | Build evidence requires pinned Android release/API, build ID `CP2A.260605.016`, security patch `2026-06-05`, `userdebug`, exact resolved manifest and hashed core images; no real output has passed this gate yet |
| Dedicated AOSP builder workflow | Manual-only self-hosted exact-tag sync/stage/build path binds one source commit to preflight, manifest, closed staging, build and optional exact-product Cuttlefish runtime/smoke evidence; no successful AOSP run recorded yet |
| AOSP failure evidence | Failed builds retain only bounded diagnostics and immutable failure evidence; reports remain `FAILED_NOT_READY` with build/runtime/status-promotion/device-write/flash/root flags false |
| Cuttlefish runtime evidence | Exact product/device/manufacturer/API/build-type/fingerprint/package/launcher collector plus build/runtime fingerprint binding implemented; not yet run against a built SwirPhoneOS image |
| Cuttlefish app launch smoke | Exact-identity local-emulator gate + package-local launch + resumed-activity confirmation implemented for all source-ready apps; not yet run against a built SwirPhoneOS image |
| Cuttlefish product | `PRODUCT_PACKAGES` includes Phone, Messages, Calculator, Settings, Files, DeviceCare, Update, Privacy, Clock, Notes, Calendar, Gallery, Recorder, Contacts, Apps and SwirRoot; **not built or booted** |
| Swir Phone | `ANDROID_SOURCE`; permission-free keypad + host-tested dial normalization + explicit Android `ACTION_DIAL` hand-off; direct calls, default-dialer/in-call UI and recent calls are not implemented or verified |
| Swir Messages | `ANDROID_SOURCE`; permission-free local compose/draft flow + host-tested recipient/body bounds + explicit Android `ACTION_SENDTO`/`smsto:` hand-off; no direct SMS send/read path, MMS or conversation history; runtime/carrier behavior not verified |
| SwirCalculator | `ANDROID_SOURCE`; basic math host-tested; Android runtime not verified |
| SwirSettings | `ANDROID_SOURCE`; reviewed settings routes/search/device state; Android runtime not verified |
| SwirFiles | `ANDROID_SOURCE`; user-granted SAF file operations; Android runtime not verified |
| SwirDeviceCare | `ANDROID_SOURCE`; permission-free framework diagnostics; Android runtime not verified |
| SwirUpdate | `ANDROID_SOURCE`; read-only state + SHA-256/RSA metadata verification; install path disabled |
| SwirPrivacy | `ANDROID_SOURCE`; reviewed privacy routes; live indicators/history not implemented |
| SwirClock | `ANDROID_SOURCE`; time/stopwatch/timer/user-visible alarm hand-off |
| SwirNotes | `ANDROID_SOURCE`; local SQLite CRUD/search/share/Markdown export, 8 locales |
| SwirCalendar | `ANDROID_SOURCE`; local SQLite agenda/date-time editing/share/ICS export, 8 locales; CalendarProvider bridge not implemented |
| SwirGallery | `ANDROID_SOURCE`; scoped MediaStore browse/search/open/share and owner-confirmed deletion; albums not implemented |
| SwirRecorder | `ANDROID_SOURCE`; foreground-only private AAC/MPEG-4 recording, pause/resume/stop/playback/export/delete; exact-device audio behavior not verified |
| SwirContacts | `ANDROID_SOURCE`; scoped ContactsProvider browse/search with exactly `READ_CONTACTS`, Android-managed create/edit, explicit vCard import hand-off and user-selected vCard export; runtime not verified |
| Swir Apps | `ANDROID_SOURCE`; permission-free local launcher catalog with version and signing-certificate SHA-256 provenance plus launch/app-details navigation; remote catalog/install/update status is not implemented |
| SwirRoot | `ANDROID_SOURCE`; localized owner UI + non-exported status/diagnostic service + host-tested gate policy; mutation backend hard-disabled, supported builds = 0, state = `UNAVAILABLE` |
| Android source safety | Validator scans all production Java for forbidden execution/network/broad-storage primitives and exact per-app permission allowlists; Phone and Messages are permission-free and cannot gain direct call/SMS primitives, Contacts is limited to `READ_CONTACTS`, Gallery to media-read permissions, Recorder to `RECORD_AUDIO`, other permission-free apps remain permission-free, and SwirRoot retains additional no-mutation gates |
| Android source localization | Sixteen source-ready apps have EN/PL/NB/DE/ES/FR/PT/AR catalogs; source lint checks key, formatter/plural and common Java UI-literal contracts; runtime locale/RTL behavior remains unverified |
| Source capability accounting | Schema-v3 source summary tracks unfinished capabilities per app (for example `phone:in_call`, `phone:recent_calls`, `messages:mms`, `messages:conversation_history`, `calendar:provider_bridge` and `apps:update_status`) so one app implementing a shared capability name cannot hide another app's unfinished work |
| System apps | 20-app registry: **16 `ANDROID_SOURCE`, 4 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified** |
| SwirRoot host policy | `write_operations_enabled=false`; supported root builds = 0; exploit/bypass methods forbidden |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/GSI image | Not built |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated; no real evidence set captured/reviewed |
| Backup/install/recovery/stock restore | Evidence foundations implemented locally; no verified partition map, write engine or physical install/restore test |
| Signing/OTA | Verification primitives/source contracts only; release signing/update/rollback runtime path not implemented |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, provenance/evidence rejection logic, desktop packaging, exact staging-tree closure, read-only hardware correlation, local transaction safety, Cuttlefish smoke parsing, exact Android permission allowlists and pure-Java policies for the sixteen source-ready apps. It cannot establish Android runtime compatibility, working telephony, carrier SMS/MMS delivery, working root, recovery safety or hardware support. AOSP/platform credit remains blocked until the pinned source synchronizes and builds; emulator credit remains blocked until that exact image boots and reviewed runtime plus app-smoke evidence is recorded. The source-app expansion grants no weighted milestone credit.
