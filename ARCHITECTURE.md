# Architecture

SwirPhoneOS is the mobile SwirOS project: Android-compatible AOSP userspace on the Linux kernel, not a bare-metal Kali distribution and not the desktop SWIR OS project.

## Platform

Keep the layers modular: Swir applications and UX; launcher/SystemUI/settings overlays; isolated framework additions; upstream Android framework; vendor/HAL interface; per-device kernel and firmware. Prefer overlays/product configuration over invasive framework forks. Upstream baseline selection and a pinned source manifest are still pending. `swir_core/` does not contain an Android source checkout or a product build yet.

## Compatibility

Build ARM64 GSI where vendor/Treble constraints allow, plus explicit device packs and full ports when needed. Support belongs to an exact model, firmware baseline and tested build, not permanently to a codename. Future levels are EXPERIMENTAL, BASIC, DAILY and FULL; the current avicii target is below all of them: PLANNED_NOT_SUPPORTED. Bootloader policy, partition layout, vendor code and hardware behavior prevent a universal guarantee. See `docs/SOURCES.md`.

## Host tools

The current Python package has no third-party runtime dependencies. The read-only ADB adapter accepts only device listing and ten fixed getprop reads, selects a single authorized USB device and rechecks the endpoint after inspection. It never treats Android-reported properties as trusted flashing identity. Error output deliberately excludes raw command output and serials. No generic subprocess or downloaded device-pack script execution is exposed by the CLI.

The next layer is a profile registry and schema validator, followed by read-only Fastboot/FastbootD adapters. Destructive operations need independent exact-device and partition verification, trusted signed image manifests, interactive owner confirmation, a durable state journal and a proven recovery path. None of those write capabilities exists now.

## Desktop and UX

Flash Studio targets Windows first and Linux second. Select the GUI toolkit only after packaging and accessibility evaluation. The GUI must have responsive layout, clear diagnostic states, system-language initialization with English fallback, extensible translations, application icon, offline recovery documentation and `by Swir` plus the GitHub link. A CLI prototype is not a Windows EXE release.

## Updates and trust

Plan separate development/beta/stable channels and signed update metadata independent of HTTPS transport. Keep release keys private and outside source control. Hashes detect changes but are not a substitute for trusted signatures. Device-specific AVB, encryption and anti-rollback rules must be designed and tested before installation support. Do not automatically disable verification or relock a bootloader.

## Resource gates

A full AOSP build is a different workload from host unit tests. The checked upstream setup guidance specifies substantial Linux x86-64 build resources; record available disk/RAM and obtain an appropriate build runner before downloading the tree. Do not purchase infrastructure or claim a compiled ROM when only documentation or Python tests exist.
