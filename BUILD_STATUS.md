# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-17**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB / Fastboot | Strict local-USB allowlists implemented; ADB now records exact firmware/build + verified-boot/slot hints, Fastboot optionally records bounded partition size/slot hints; no physical USB evidence captured yet |
| Cross-transport hardware evidence | Integrity-hashed ADB+Fastboot correlation and exact transaction/profile/build matching implemented; always `hardware_verified=false`, `write_allowed=false`, `flash_allowed=false`, `root_allowed=false`; no real avicii observation captured yet |
| Device profile registry | Metadata-only schema; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI and Windows developer packaging; no write controls |
| Transaction evidence | Local-only schema-v1 plan validation, exact install+rollback artifact size/SHA-256 verification and create-only fsynced recovery journal implemented; plan can be compared to correlated read-only device evidence; `write_allowed=false`, owner confirmation not recorded, no device commands |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace | Exact-tag plan, resolved-manifest SHA validation, bounded manifest/fragment staging and fail-closed build-artifact provenance tooling implemented |
| Dedicated AOSP builder workflow | Manual-only self-hosted exact-tag sync/stage/build path optionally launches the exact built Cuttlefish product, waits for strict boot evidence, app-smokes all source-ready packages and cleans up; no successful AOSP run recorded yet |
| Cuttlefish runtime evidence | Read-only exact product/device/manufacturer/API/build-type/fingerprint/package/launcher collector plus build/runtime fingerprint binding implemented; not yet run against a built SwirPhoneOS image |
| Cuttlefish app launch smoke | Exact-identity local-emulator gate + package-local `am start -W` + resumed-activity confirmation implemented for all source-ready apps; not yet run against a built SwirPhoneOS image |
| Cuttlefish product | `PRODUCT_PACKAGES` includes Calculator, Settings, Files, DeviceCare, Update, Privacy, Clock, Notes, Calendar and SwirRoot; **not built or booted** |
| SwirCalculator | `ANDROID_SOURCE`; basic math host-tested; Android runtime not verified |
| SwirSettings | `ANDROID_SOURCE`; reviewed settings routes/search/device state; Android runtime not verified |
| SwirFiles | `ANDROID_SOURCE`; user-granted SAF file operations; Android runtime not verified |
| SwirDeviceCare | `ANDROID_SOURCE`; permission-free framework diagnostics; Android runtime not verified |
| SwirUpdate | `ANDROID_SOURCE`; read-only state + SHA-256/RSA metadata verification; install path disabled |
| SwirPrivacy | `ANDROID_SOURCE`; reviewed privacy routes; live indicators/history not implemented |
| SwirClock | `ANDROID_SOURCE`; time/stopwatch/timer/user-visible alarm hand-off |
| SwirNotes | `ANDROID_SOURCE`; local SQLite CRUD/search/share/Markdown export, 8 locales |
| SwirCalendar | `ANDROID_SOURCE`; local SQLite agenda/date-time editing/share/ICS export, 8 locales; provider bridge not implemented |
| SwirRoot | `ANDROID_SOURCE`; original localized owner UI + non-exported status/diagnostic service + bounded private review audit + host-tested gate policy; mutation backend hard-disabled, supported builds = 0, state = `UNAVAILABLE`; guided enable/unroot not implemented |
| Android source safety | Validator checks all production Java files for forbidden execution/network/storage primitives; SwirRoot additionally requires disabled mutation support and exact-build/profile/rollback/journal/owner gates |
| System apps | 20-app registry: **10 `ANDROID_SOURCE`, 10 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified** |
| SwirRoot host policy | `write_operations_enabled=false`; supported root builds = 0; exploit/bypass methods forbidden |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/GSI image | Not built |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated; cross-transport tooling exists but no real evidence set has been captured/reviewed |
| Backup/install/recovery/stock restore | Transaction + correlated-device evidence foundations implemented locally; no verified partition map, write engine or physical install/restore test, so milestone remains incomplete |
| Signing/OTA | Verification primitives/source contracts only; release signing/update/rollback runtime path not implemented |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, provenance/bundle rejection logic, desktop startup/packaging, staging safety, read-only hardware correlation, local transaction artifact/journal safety, Cuttlefish smoke allowlist/parsing logic, source-wide Android safety rules and pure-Java logic/policies for the ten source-ready apps. It cannot establish Android runtime compatibility, working root, recovery safety or hardware support. AOSP/platform credit remains blocked until the pinned source synchronizes and builds; emulator credit remains blocked until the resulting exact image boots and reviewed runtime plus app-smoke evidence is recorded. Install/restore credit remains blocked until an exact physically verified device/profile has a tested write and rollback/stock-restore path.
