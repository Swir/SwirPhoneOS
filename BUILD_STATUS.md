# Build Status

Version: **0.0.2.dev0**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Local Linux/Python 3.13.5 unit tests | 41/41 passed; fixtures/mocks, no USB phone |
| Python compileall | Passed for swirphoneos and tests |
| CLI status | Passed; weighted progress 2%, beta 0/9 |
| CLI gate | Correctly returns exit 2 / publication blocked |
| Windows/Linux Python 3.11–3.14 CI | Workflow configured; inspect Actions for the actual final-commit result |
| Live ADB on a phone | Not tested |
| Fastboot/FastbootD | Not implemented |
| GUI / Windows EXE | Not built |
| AOSP baseline/source lock | Not selected/pinned |
| Android/GSI image | Not built |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Beta Release | Blocked; no release published |

The local host results do not establish Windows or Android runtime compatibility. Read-only inspection must be tested on real authorized USB hardware before its milestone is completed. CI runs only host tests and cannot establish phone compatibility.
