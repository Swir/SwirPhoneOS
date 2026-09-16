# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB / Fastboot | Strict read-only allowlists implemented; no physical USB evidence yet |
| Device profile registry | Metadata-only schema; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI and Windows developer packaging; no write controls |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace | Exact-tag plan, resolved-manifest SHA validation, bounded manifest/fragment staging and fail-closed build-artifact provenance tooling implemented |
| Dedicated AOSP builder workflow | Manual-only self-hosted workflow added for exact-tag sync, staging, build and evidence capture; no successful AOSP run recorded yet |
| Cuttlefish runtime evidence | Read-only exact product/device/manufacturer/API/build-type/fingerprint/package/launcher collector plus build/runtime fingerprint binding implemented; not yet run against a built SwirPhoneOS image |
| Cuttlefish product | `PRODUCT_PACKAGES` includes Calculator, Settings, Files, DeviceCare, Update, Privacy, Clock, Notes and Calendar; **not built or booted** |
| SwirCalculator | `ANDROID_SOURCE`; basic math host-tested; Android runtime not verified |
| SwirSettings | `ANDROID_SOURCE`; reviewed settings routes/search/device state; Android runtime not verified |
| SwirFiles | `ANDROID_SOURCE`; user-granted SAF file operations; Android runtime not verified |
| SwirDeviceCare | `ANDROID_SOURCE`; permission-free framework diagnostics; Android runtime not verified |
| SwirUpdate | `ANDROID_SOURCE`; read-only state + SHA-256/RSA metadata verification; install path disabled |
| SwirPrivacy | `ANDROID_SOURCE`; reviewed privacy routes; live indicators/history not implemented |
| SwirClock | `ANDROID_SOURCE`; time/stopwatch/timer/user-visible alarm hand-off |
| SwirNotes | `ANDROID_SOURCE`; local SQLite CRUD/search/share/Markdown export, 8 locales |
| SwirCalendar | `ANDROID_SOURCE`; local SQLite agenda/date-time editing/share/ICS export, 8 locales; provider bridge not implemented |
| System apps | 20-app registry: **9 `ANDROID_SOURCE`, 11 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified** |
| SwirRoot | Fail-closed policy only; writes disabled; supported root builds = 0 |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/GSI image | Not built |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Verification primitives/source contracts only; release signing/update/rollback runtime path not implemented |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, provenance/bundle rejection logic, desktop startup/packaging, staging safety and pure-Java logic/policies for the nine source-ready apps. It cannot establish Android runtime compatibility or hardware support. AOSP/platform credit remains blocked until the pinned source synchronizes and builds; emulator credit remains blocked until the resulting image boots and reviewed runtime evidence is recorded.
