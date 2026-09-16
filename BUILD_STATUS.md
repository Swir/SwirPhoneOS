# Build Status

Version: **0.0.2.dev0 + unreleased host diagnostics**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Main baseline local Linux/Python 3.13.5 unit tests | 41/41 passed; fixtures/mocks, no USB phone |
| New Fastboot/profile/i18n/report/platform unit coverage | Added host-side tests; final PR matrix is the authoritative result |
| Python compileall | Covered by Windows/Linux CI for swirphoneos and tests |
| CLI status | Main baseline passed; weighted progress remains 2%, beta 0/9 |
| CLI gate | Correctly blocks publication while beta evidence is incomplete |
| Windows/Linux Python 3.11–3.14 CI | Required on the exact feature head and again after merge; inspect Actions for final status |
| SwirPhoneStudio source GUI | Implemented as read-only developer preview; physical Windows launch/USB smoke still required |
| System-language handling | PL/NO/EN mapping with English fallback covered by unit tests |
| Sanitized JSON report export | Implemented with sensitive-key rejection and unit coverage |
| Live ADB on a phone | Not tested |
| Fastboot/FastbootD | Read-only implementation added; mocked host tests only, no physical USB validation |
| Device profile registry | Strict metadata-only schema-v1 validator added; current avicii profile remains not supported |
| Android 17 AOSP candidate | Discovery metadata validated offline; `CANDIDATE_NOT_PINNED`, no source sync/build |
| Packaged Windows EXE | Not built |
| AOSP reproducible source lock | Not completed; resolved manifest snapshot/checksum still required |
| Android/GSI image | Not built |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Beta Release | Blocked; no release published |

Host tests do not establish Windows USB-driver behavior, Android runtime compatibility or phone support. The desktop-diagnostics milestone remains incomplete until the GUI and diagnostics have real Windows/USB evidence. The AOSP milestone remains incomplete until the baseline is reproducibly pinned and built. No profile can authorize flashing under schema v1.
