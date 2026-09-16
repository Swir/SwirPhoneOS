# Build Status

Version: **0.0.2.dev0 + unreleased Android-source/platform hardening**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Foundation | Host contracts/tests exist; foundation is the only completed weighted milestone |
| Read-only ADB | Strict allowlist implemented; no physical USB evidence yet |
| Read-only Fastboot/FastbootD | Strict getvar-only core implemented; no physical USB evidence yet |
| Device profile registry | Metadata-only schema; OnePlus Nord AC2003/avicii remains `PLANNED_NOT_SUPPORTED` |
| SwirPhoneStudio | Multilingual ADB/Fastboot inspection GUI and Windows developer packaging; no write controls |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` identity preserved; `PINNED_NOT_BUILT` |
| AOSP workspace evidence | Exact-tag plan, resolved-manifest SHA validation and bounded manifest-whitelisted staging implemented |
| Cuttlefish product | x86_64 product source plus `PRODUCT_PACKAGES += SwirCalculator SwirSettings`; **not built or booted** |
| SwirCalculator | `ANDROID_SOURCE`: real AOSP app source, host-tested BigDecimal engine, original icon/UI, 8 locale resources, RTL/accessibility contract; Android build/runtime not verified |
| SwirSettings | `ANDROID_SOURCE`: permission-free settings hub source, reviewed public Android settings routes, search, real build/device status, original icon/UI and 8 locale resources; Android build/runtime not verified |
| System apps | 20-app registry: 2 `ANDROID_SOURCE`, 18 `HOST_CONTRACT`, 0 `ANDROID_RUNTIME`, 0 hardware-verified |
| SwirRoot | Fail-closed policy only; writes disabled; supported root builds = 0 |
| Resolved full AOSP source manifest | Not captured from a real synchronized workspace |
| Android/GSI image | Not built |
| Cuttlefish boot | Not performed; no `sys.boot_completed=1` evidence |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Project ledger | **2%**, 1/10 weighted milestones; **Beta 0/9** |
| Beta Release | Blocked; no release published |

Host CI can verify Python contracts, desktop UI startup/packaging, manifest staging safety, SwirCalculator pure-Java logic and the SwirSettings reviewed route catalog. It cannot establish Android runtime compatibility or hardware support. AOSP/platform credit therefore remains blocked until the pinned source is synchronized and the product actually builds; emulator credit remains blocked until the resulting image boots and runtime evidence is recorded.
