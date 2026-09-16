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

The canonical ledger is `project.json`. Weights sum to 100; completion is the sum of weights for gates that are actually complete. One bar segment is 5 percentage points, rounded down. This is milestone accounting, not an estimate of elapsed work, remaining time or supported hardware. Beta readiness is tracked separately: **0/9 gates passed**.

| Gate | Weight | Completion evidence required |
| --- | ---: | --- |
| foundation | 2 | Architecture, explicit safety/release contracts, executable ledger validation and passing local negative tests |
| desktop_diagnostics | 8 | Tested read-only ADB/Fastboot/FastbootD diagnostics, profile validation, useful desktop UI and real Windows/USB smoke evidence |
| aosp_baseline | 10 | Pinned upstream manifest, reproducible environment and completed platform build |
| emulator_boot | 10 | Swir product boots into usable Android UI; recorded runtime and regression tests |
| gsi_validation | 10 | Built ARM64 GSI plus relevant Treble/VTS compatibility evidence and known-issues matrix |
| reference_hardware | 25 | Exact-model physical boot, firmware baseline, telephony/connectivity/audio/cameras/sensors/storage/charging/thermal/suspend/encryption validation |
| install_restore | 15 | User-confirmed safe installation and tested recovery/stock restore on the same device/firmware profile |
| swir_ux | 8 | Integrated launcher/SystemUI/settings and essential Swir system-app experience, i18n, accessibility and visual/runtime review, not static mockups |
| security_ota | 8 | Release signing, update authenticity, security review, tested update/rollback/recovery behavior, including SwirRoot state interaction where enabled |
| beta_release | 4 | All beta gates reviewed, actual images and Windows package published and post-release verified |

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

The read-only ADB CLI and Flash Studio GUI, strict Fastboot/FastbootD inspection, and schema-v1 device registry are slices of `desktop_diagnostics`, not completion of its 8-point gate. The GUI has native-window tests, asynchronous ADB inspection, a data-driven localization runtime and local report export. A Windows one-file developer packaging workflow now builds the existing read-only GUI and smoke-tests the frozen executable before uploading a short-lived CI artifact. That packaging pipeline is not a release and cannot substitute for real local Windows/USB ADB + Fastboot/FastbootD evidence. Fastboot/profile GUI integration and physical USB validation remain outstanding.

The Android 17 / API 37 baseline has advanced from moving discovery metadata to an exact official release-tag pin. `platform/aosp_baseline.json` is now schema v2 / `PINNED_NOT_BUILT` and preserves `android-17.0.0_r1`, annotated tag object `7a9e46ba6ed424f922a3457f4964e67e0b966201`, manifest commit `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f` and tree `1541b7154f1532032baf7c73f222256cc29e8cfb`. A bounded read-only build-host preflight now checks the official high-level Linux/x86-64, glibc, disk, RAM and Git/Repo requirements without downloading or modifying the host. No source sync or platform build is claimed, so `aosp_baseline` remains incomplete and global progress stays 2%.

The first-party app suite and SwirRoot product scope are defined in `docs/SYSTEM_APPS.md`. A machine-readable 20-app registry locks package namespace, delivery phase, hardware dependence, beta-criticality and current implementation status. A fail-closed SwirRoot policy makes `UNAVAILABLE` the mandatory default on unverified builds and rejects unsafe policy changes. These are host-side engineering contracts, not Android runtime implementation, so the global percentage remains unchanged.

The localization foundation is data-driven and validates eight current Flash Studio catalogs, including explicit RTL metadata for Arabic, BCP-47-style resolution, English fallback and placeholder compatibility. `docs/I18N.md` defines the future system-wide Android resource contract. This is meaningful preparation for `swir_ux`, but it does not complete the UX milestone until the actual mobile UI uses and passes it.

## System app delivery track

The essential SwirPhoneOS suite is developed in parallel with the platform rather than after the ROM is otherwise complete.

### Emulator/core phase

- [ ] Shared SwirPhoneOS design system, icon rules, package naming, localization and permission conventions integrated into the Android product tree.
- [ ] Swir Settings usable in the emulator with real platform-backed settings.
- [ ] Swir Files usable in the emulator with safe local file operations.
- [ ] Swir Update exposes signed-channel/update state and recovery hand-off appropriate to the development channel.
- [ ] Swir Privacy and Swir Device Care expose real emulator/platform state rather than placeholder cards.
- [ ] Swir Clock and Swir Calculator provide functional daily-use baseline apps.

### Reference-hardware phase

- [ ] Swir Phone/Contacts/Messages validated against the exact reference telephony stack.
- [ ] Swir Camera/Gallery validated against the exact reference camera/media stack.
- [ ] Swir Recorder validated with the reference audio stack.
- [ ] Swir Backup/restore paths aligned with the exact reference encryption/storage/recovery behavior.
- [ ] Calendar, Notes, Browser, Weather and Swir Apps/Software Center integrated to beta-appropriate quality.

### SwirRoot phase

- [ ] SwirRoot displays authoritative ROOT OFF / ROOT ON / UNAVAILABLE state for the exact build/profile.
- [ ] Enable-root path requires explicit support, owner confirmation, verified rollback material and operation journaling.
- [ ] Unroot restores the expected non-root boot/system state on the exact tested build/profile.
- [ ] Per-app root authorization is deny-by-default, revocable and auditable when root service implementation exists.
- [ ] SwirRoot state is integrated with Swir Update, recovery and SwirPhoneStudio.
- [ ] Physical enable -> reboot -> use -> disable -> recovery validation completed before any beta claim for root support.

These track checkboxes are engineering sub-deliverables and do not independently change the 10-gate weighted progress calculation.

## Next engineering work

For the platform, run the new read-only build-host preflight on the intended AOSP builder, then initialize/sync the official manifest at the exact `android-17.0.0_r1` revision. Preserve `repo manifest -r`, its SHA-256 and Repo/Git/JDK/host versions. Complete the first platform product build before any `aosp_baseline` milestone credit. Then target Cuttlefish/emulator boot before claiming GSI or physical-phone support.

Harden **SwirPhoneStudio / Flash Studio** by integrating the existing read-only Fastboot/FastbootD inspection and profile registry into the tested GUI. The Windows packaging workflow should remain a developer artifact pipeline until frozen-executable smoke, local Windows runtime and actual USB evidence are all collected. No write controls are enabled at this stage.

In parallel, translate the host-side app/i18n contracts into the **actual AOSP product tree**: package namespace policy, shared resource conventions, RTL-aware design tokens, accessibility rules and first real emulator applications. Prioritize Settings, Files, Update, Privacy and Device Care. The registry status must move from `HOST_CONTRACT` to `ANDROID_RUNTIME` only when working code is built and exercised; static package shells do not count.

After emulator/GSI evidence exists, expand device packs from metadata-only profiles into independently reviewed installation/recovery plans. No generic write operation may be enabled merely because a device reports Treble, a codename or an unlocked bootloader. Each supported hardware profile requires an explicit stock-recovery path and physical evidence.

SwirRoot implementation begins only after the boot/update/recovery contracts are concrete enough to support deterministic rollback. `swirroot/policy.json` must remain fail-closed until an exact-build Android root service and physical enable/unroot/recovery evidence exist. It must use supported build/image paths, not bootloader exploits, and root support remains an exact-build/device capability rather than a universal promise.

## Release stages

Developer preview: usable emulator/GSI plus developer instructions. Alpha: physical-device boot and documented recovery. Beta: all mandatory `BETA_RELEASE_GATE.md` checks passed for the exact release candidate. Stable: stricter sustained runtime, update, recovery and security validation.

Device expansion follows evidence, not manufacturer checklists. GSI, device-pack and full-port support are separate strategies. Unsupported or permanently locked devices remain unsupported rather than getting a risky generic flash script.
