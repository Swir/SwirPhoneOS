# Build Status

Version: **0.0.2.dev0 + unreleased diagnostics/platform hardening**. Updated: **2026-09-16**.

| Area | Verified state |
| --- | --- |
| Prior foundation host suite | 41 tests; foundation commit 91ceaf48b498ea8bf1e7ac0a941b96621f0aca4b passed Windows/Linux CI |
| Merged desktop tests, local Linux/Python 3.13.5 | 46/46 passed, including 7 real Tk-window tests; synthetic inspection only |
| Current host contract changes | Pinned AOSP baseline, build-host preflight and Windows packaging pipeline added; current PR CI is authoritative |
| Python compileall | Covered by Windows/Linux CI for all host sources/tests |
| GUI entry-point smoke | Native source GUI smoke remains in Windows/Linux CI; frozen Windows EXE smoke is now required by the packaging workflow |
| GUI layout review | Merged desktop slice recorded local 900x720 review and 640x500 minimum-size automated check |
| Project ledger | Unchanged: weighted progress 2%, beta 0/9; publication guard remains active |
| Windows/Linux Python 3.11–3.14 CI | Existing native GUI checks preserved; pinned-baseline and read-only build-host preflight validation added |
| Live ADB on a phone | Not tested |
| Fastboot/FastbootD | Strict read-only core implemented; mocked host tests only, no physical USB validation |
| Device profile registry | Strict metadata-only schema-v1 validator implemented; avicii remains not supported |
| Flash Studio GUI | Implemented as Python/Tk source; eight data-driven locales, read-only ADB scan and local JSON export; Fastboot/profile GUI integration pending |
| Packaged Windows EXE | Reproducible one-file PyInstaller 6.22.3 workflow added for Windows x64/Python 3.14 with frozen-GUI smoke and SHA-256 artifact; no release claim until CI succeeds |
| Android 17 AOSP baseline | Exact `android-17.0.0_r1` manifest identity preserved; status `PINNED_NOT_BUILT`, no source sync/build |
| AOSP manifest pin | Tag object `7a9e46ba6ed424f922a3457f4964e67e0b966201` -> commit `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f` -> tree `1541b7154f1532032baf7c73f222256cc29e8cfb` |
| AOSP build-host preflight | Read-only checker implemented for Linux/x86-64, glibc, 400 GiB free disk, 64 GiB RAM, Git/Repo and KVM visibility; does not mutate the host |
| Resolved full source manifest | Not captured; requires actual source sync followed by `repo manifest -r` and SHA-256 preservation |
| Android/GSI image | Not built |
| Physical avicii support | Not validated |
| Backup/install/recovery/stock restore | Not implemented or hardware-tested |
| Signing/OTA | Design only |
| Beta Release | Blocked; no release published |

Host tests can validate Python behavior, GUI startup, schema rules, exact baseline metadata and packaging mechanics, but they cannot establish Android compatibility or certify hardware. `desktop_diagnostics` stays incomplete until real Windows/USB evidence exists. `aosp_baseline` stays incomplete until the pinned source is actually synced, the resolved multi-repository manifest/toolchain metadata is preserved and a platform build succeeds. Project progress therefore remains **2%**, with **0/9 beta gates** passed.
