# SwirPhoneOS Roadmap

<!-- SWIR-ROADMAP-STANDARD:v1 -->
![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Roadmap](https://img.shields.io/badge/ROADMAP-2%25-blue)
![Done](https://img.shields.io/badge/DONE-1%2F10_milestones-blue)
![Status](https://img.shields.io/badge/STATUS-foundation-orange)

## Overall progress

**2% — weighted engineering milestones.**

`[--------------------] 2%`

| Completed milestones | Remaining | Total | Weighted progress |
| --- | --- | --- | --- |
| 1 | 9 | 10 | 2% |

The canonical ledger is `project.json`. Weights total 100 and only evidence-complete gates contribute. Source scaffolding, host tests and desktop packaging do not substitute for an Android build, boot or physical-device validation. Beta readiness is tracked separately: **0/9 gates passed**.

| Gate | Weight | Completion evidence required |
| --- | ---: | --- |
| foundation | 2 | Architecture, safety/release contracts, executable ledger validation and negative tests |
| desktop_diagnostics | 8 | Tested read-only ADB/Fastboot/FastbootD diagnostics, profile validation, useful desktop UI and real Windows/USB smoke evidence |
| aosp_baseline | 10 | Pinned upstream manifest, reproducible environment and completed platform build |
| emulator_boot | 10 | Swir product boots into usable Android UI; recorded runtime and regression tests |
| gsi_validation | 10 | Built ARM64 GSI plus relevant Treble/VTS evidence and known-issues matrix |
| reference_hardware | 25 | Exact-model physical boot and validated telephony/connectivity/audio/cameras/sensors/storage/charging/thermal/suspend/encryption |
| install_restore | 15 | User-confirmed safe installation and tested recovery/stock restore on the same device/firmware profile |
| swir_ux | 8 | Integrated launcher/SystemUI/settings and essential Swir apps, i18n, accessibility and visual/runtime review |
| security_ota | 8 | Release signing, update authenticity, security review, tested update/rollback/recovery including SwirRoot interaction where enabled |
| beta_release | 4 | All beta gates reviewed, real images and Windows package published and post-release verified |

## Verified milestone checklist

- [x] foundation
- [ ] desktop_diagnostics
- [ ] aosp_baseline
- [ ] emulator_boot
- [ ] gsi_validation
- [ ] reference_hardware
- [ ] install_restore
- [ ] swir_ux
- [ ] security_ota
- [ ] beta_release

## Current verified engineering slices

### Desktop

Read-only ADB/Fastboot/FastbootD diagnostics, metadata-only profile hints, multilingual SwirPhoneStudio and Windows one-file developer packaging exist. Real owner-controlled Windows USB ADB + Fastboot/FastbootD evidence is still missing, so `desktop_diagnostics` remains incomplete.

### Platform

Android 17 / API 37 is pinned to `android-17.0.0_r1`. A read-only build-host preflight, exact-tag workspace plan, resolved-manifest validator and bounded source staging path exist. The x86_64 Cuttlefish product definition is checked in. No completed source sync, Kati/Soong build or Cuttlefish boot is claimed, so `aosp_baseline` and `emulator_boot` remain incomplete.

### Android application source

SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate and SwirPrivacy are now **`ANDROID_SOURCE`** and included in the SwirPhoneOS Cuttlefish product definition. Calculator provides host-tested BigDecimal basic math. Settings exposes localized search, real build/device status and reviewed settings routes. Files uses a user-granted Storage Access Framework tree rather than broad storage permissions. Device Care reads real framework device/security-patch, battery/charging, storage, memory and thermal state without privileged permissions.

Update adds real local channel/build state and host-tested SHA-256/RSA signed-metadata verification, while deliberately omitting package download/staging/recovery installation until the platform update path is designed and verified. Privacy adds a host-tested exact allowlist of authoritative Android privacy/permission settings routes, while live privacy indicators and access history remain future platform work.

All six have original icons/UI, eight locale resource sets including Arabic/RTL metadata, source-level safety validation and bounded AOSP staging. **None is `ANDROID_RUNTIME`: no pinned-AOSP APK build or emulator execution has happened yet.** Calculator scientific math, Update staged/recovery state and Privacy live indicators/access history remain declared targets, not implemented capabilities. Source-only progress therefore does not complete the emulator/core delivery checkboxes or change the weighted project percentage.

### SwirRoot

SwirRoot is still a fail-closed policy only. No exact-build root service, mutation path or physical enable/unroot/recovery evidence exists; supported root builds remain zero.

## System app delivery track

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the Android product tree.
- [ ] Swir Settings usable in the emulator with real platform-backed settings.
- [ ] Swir Files usable in the emulator with safe local file operations.
- [ ] Swir Update exposes signed-channel/update state and recovery hand-off appropriate to the development channel.
- [ ] Swir Privacy and Swir Device Care expose real emulator/platform state rather than placeholder cards.
- [ ] Swir Clock and Swir Calculator provide functional daily-use baseline apps.

> Source progress: SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate and SwirPrivacy now contain meaningful Android source and host-tested pure-Java logic/contracts, but their checkboxes stay open until the relevant capabilities are built and exercised inside the SwirPhoneOS emulator image. Source-only work receives no weighted gate credit.

### Reference-hardware phase

- [ ] Swir Phone/Contacts/Messages validated against the exact reference telephony stack.
- [ ] Swir Camera/Gallery validated against the exact reference camera/media stack.
- [ ] Swir Recorder validated with the reference audio stack.
- [ ] Swir Backup/restore aligned with exact encryption/storage/recovery behavior.
- [ ] Calendar, Notes, Browser, Weather and Swir Apps integrated to beta-appropriate quality.

### SwirRoot phase

- [ ] Authoritative ROOT OFF / ROOT ON / UNAVAILABLE state for the exact build/profile.
- [ ] Enable-root requires explicit support, owner confirmation, verified rollback material and journaling.
- [ ] Unroot restores the expected non-root boot/system state on the exact build/profile.
- [ ] Per-app root authorization is deny-by-default, revocable and auditable.
- [ ] SwirRoot integrates with Swir Update, recovery and SwirPhoneStudio.
- [ ] Physical enable -> reboot -> use -> disable -> recovery validation before any beta root claim.

These sub-deliverables do not independently change the ten-gate weighted percentage.

## Next engineering work

1. On a capable Linux x86-64 AOSP builder, run preflight, initialize/sync exact `android-17.0.0_r1`, preserve `repo manifest -r` + SHA-256/tool versions, stage the manifest-whitelisted `vendor/swir/` product/app bundle, and compile `swirphoneos_cf_x86_64-aosp_current-userdebug`.
2. Boot the resulting image in Cuttlefish and preserve `sys.boot_completed=1`, SystemUI plus Calculator/Settings/Files/DeviceCare/Update/Privacy runtime evidence. Only then can source status move toward `ANDROID_RUNTIME` and platform/emulator gates be reconsidered.
3. After the real runtime exists, connect SwirUpdate to a signed metadata/channel service and a rollback-aware staged update/recovery contract; add platform-backed privacy indicators/access-history only through reviewed Android APIs. Keep all write/install paths disabled until rollback/recovery is proven.
4. Add Swir Clock as the next permission-minimal daily-use emulator app and continue the shared SwirPhoneOS visual/accessibility system.
5. Continue hardening SwirPhoneStudio; the next desktop gate evidence is an actual Windows USB read-only ADB + Fastboot/FastbootD smoke on an owner-controlled device.
6. After emulator/GSI evidence, expand device packs into reviewed installation/recovery plans. Never enable generic writes from Treble/codename/unlocked state alone.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: every mandatory `BETA_RELEASE_GATE.md` item passed for the exact candidate. Stable: stronger sustained runtime/update/recovery/security validation.

No release gate is weakened to make a version number advance.
