# Build Status

Version: **0.0.2.dev0 + unreleased diagnostics/platform discovery**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Prior foundation host suite | 41 tests; foundation commit 91ceaf48b498ea8bf1e7ac0a941b96621f0aca4b passed Windows/Linux CI |
| Merged desktop tests, local Linux/Python 3.13.5 | 46/46 passed, including 7 real Tk-window tests; synthetic inspection only |
| New Fastboot/profile/platform tests | Portable host-side tests added; exact PR CI result is authoritative |
| Python compileall | Covered by Windows/Linux CI for all host sources/tests |
| GUI entry-point smoke | Merged desktop slice passed locally under Xvfb; CI keeps Linux/Windows native Tk smoke |
| GUI layout review | Merged desktop slice recorded local 900x720 review and 640x500 minimum-size automated check |
| Project ledger | Unchanged: weighted progress 2%, beta 0/9; publication guard remains active |
| Windows/Linux Python 3.11–3.14 CI | Existing native GUI checks preserved; device-registry and AOSP-baseline validation added |
| Live ADB on a phone | Not tested |
| Fastboot/FastbootD | Strict read-only core implemented; mocked host tests only, no physical USB validation |
| Device profile registry | Strict metadata-only schema-v1 validator implemented; avicii remains not supported |
| Flash Studio GUI | Implemented as Python/Tk source; EN/PL/NB, read-only ADB scan and local JSON export; Fastboot/profile GUI integration pending |
| Packaged Windows EXE | Not built or tested |
| Android 17 AOSP candidate | Discovery metadata recorded and validated; `CANDIDATE_NOT_PINNED`, no source sync/build |
| AOSP reproducible source lock | Not completed; resolved revision manifest/checksum/build-host record still required |
| Android/GSI image | Not built |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Beta Release | Blocked; no release published |

The merged desktop suite has display-independent and real Tk-window tests using synthetic phone reports. The new Fastboot tests mock the host subprocess boundary and do not contact a phone. CI can validate Python behavior, GUI startup, schema rules and metadata consistency, but host tests can never establish Android compatibility or certify hardware. `desktop_diagnostics` stays incomplete until real Windows/USB evidence exists, and `aosp_baseline` stays incomplete until the source is reproducibly pinned and built.
