# Build Status

Version: **0.0.2.dev0**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Prior foundation host suite | 41 tests; foundation commit 91ceaf48b498ea8bf1e7ac0a941b96621f0aca4b passed Windows/Linux CI |
| New desktop tests, local Linux/Python 3.13.5 | 46/46 passed, including 7 real Tk-window tests; synthetic inspection only |
| Python compileall | Passed for added desktop sources and tests |
| GUI entry-point smoke | Passed locally under Xvfb; opens and closes without ADB |
| GUI layout review | Local 900x720 visual review; 640x500 minimum-size automated layout check |
| Project ledger | Unchanged: weighted progress 2%, beta 0/9; publication guard remains active |
| Windows/Linux Python 3.11–3.14 CI | Native GUI checks added to all 8 target jobs; consult Actions for the exact resulting commit status |
| Live ADB on a phone | Not tested |
| Fastboot/FastbootD | Not implemented |
| Flash Studio GUI | Implemented as Python/Tk source; EN/PL/NB, read-only scan and local JSON export |
| Packaged Windows EXE | Not built or tested |
| AOSP baseline/source lock | Not selected/pinned |
| Android/GSI image | Not built |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Beta Release | Blocked; no release published |

The new desktop suite has 39 display-independent tests and 7 GUI tests. The general unit-test invocation deliberately skips the 7 GUI tests; the CI desktop step explicitly enables and runs them. GUI tests exercise real Tk windows but inject synthetic phone reports. They do not run ADB, build an EXE or certify hardware. Local results do not establish a new Windows result until the corresponding CI job actually passes. CI host results can never establish phone compatibility.
