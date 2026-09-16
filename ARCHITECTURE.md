# Architecture

SwirPhoneOS is the mobile SwirOS project: Android-compatible AOSP userspace on the Linux kernel, not a bare-metal Kali distribution and not the desktop SWIR OS project.

## Platform

Keep the layers modular: Swir applications and UX; launcher/SystemUI/settings overlays; isolated framework additions; upstream Android framework; vendor/HAL interface; per-device kernel and firmware. Prefer overlays/product configuration over invasive framework forks. Upstream baseline selection is currently represented by an Android 17 / API 37 candidate, but a revision-locked source manifest and completed platform build are still pending. `swir_core/` does not contain an Android source checkout or a product build yet.

The target architecture is therefore **Linux kernel -> Android/AOSP framework and hardware interfaces -> SwirPhoneOS platform services -> SwirPhoneOS UX and first-party apps**. Android compatibility is retained where it improves application and device support, while the visible product, system apps, services and interaction model are owned by SwirPhoneOS.

## Compatibility

Build ARM64 GSI where vendor/Treble constraints allow, plus explicit device packs and full ports when needed. Support belongs to an exact model, firmware baseline and tested build, not permanently to a codename. Future levels are EXPERIMENTAL, BASIC, DAILY and FULL; the current avicii target is below all of them: PLANNED_NOT_SUPPORTED. Bootloader policy, partition layout, vendor code and hardware behavior prevent a universal guarantee. See `docs/SOURCES.md`.

The shared core must remain device-independent. Device-specific identity, partition constraints, recovery information and eventually approved install plans belong to reviewed device profiles/ports. Automatic detection may select a candidate profile, but it must never turn an unknown phone into a supported target by inference alone.

## First-party apps and UX

SwirPhoneOS is intended to be a complete daily-use phone OS, not only a bootable image. The canonical system-app scope is defined in [`docs/SYSTEM_APPS.md`](docs/SYSTEM_APPS.md).

The first-party suite includes Phone, Contacts, Messages, Camera, Gallery, Files, Settings, Browser, Clock, Calculator, Notes, Recorder, Calendar, Weather, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot. Hardware-dependent capabilities such as telephony and camera remain per-device claims and require physical validation.

All first-party apps share one original SwirPhoneOS design system, icon family, localization architecture, accessibility rules, common permission/status surfaces and cross-app integration. Static shells and mockups do not count as implementation. Emulator-capable system apps are developed before hardware-only functions so they can participate in real runtime validation as soon as the first product image boots.

## SwirRoot

SwirRoot is a first-party, owner-controlled root manager for supported SwirPhoneOS builds and device profiles. It is not an exploit framework and must not bypass locked bootloaders or OEM protections.

The long-term root flow requires explicit support for the exact build/profile, verified rollback material, a durable operation journal, clear root state, explicit owner confirmation and a tested unroot path that restores the expected non-root boot/system state. Root status should integrate with Swir Update, recovery and SwirPhoneStudio so updates and restores cannot silently invalidate safety assumptions.

Per-app root authorization should be deny-by-default, revocable and auditable once the underlying root service exists. A global emergency-disable path is part of the design. SwirRoot is not counted as working until enable, disable and recovery behavior are exercised on the relevant build/device.

## Host tools

The current Python package has no third-party runtime dependencies. The read-only ADB adapter accepts only device listing and ten fixed getprop reads, selects a single authorized USB device and rechecks the endpoint after inspection. It never treats Android-reported properties as trusted flashing identity. Error output deliberately excludes raw command output and serials. No generic subprocess or downloaded device-pack script execution is exposed by the CLI.

A strict metadata-only device profile registry and read-only Fastboot/FastbootD adapters now exist. The registry cannot authorize writes, and the Fastboot path uses a small `getvar` allowlist with `flash_allowed: false`. Destructive operations require independent exact-device and partition verification, trusted signed image manifests, interactive owner confirmation, a durable state journal and a proven recovery path. None of those write capabilities exists now.

## Desktop and UX

SwirPhoneStudio / Flash Studio targets Windows first and Linux second. The current desktop slice uses Python/Tk and already provides the custom icon, system-language initialization with English fallback, extensible translations, asynchronous read-only ADB inspection, local report export and the `by Swir` GitHub footer. Fastboot/profile GUI integration, packaging and real Windows/USB evidence remain incomplete.

Future write-capable UI must be transaction-oriented rather than exposing raw flashing commands: detect -> verify exact profile -> validate artifacts -> show consequences -> obtain explicit confirmation -> journal every step -> verify result -> offer tested recovery/rollback. A CLI prototype or source-only GUI is not a Windows EXE release.

## Updates and trust

Plan separate development/beta/stable channels and signed update metadata independent of HTTPS transport. Keep release keys private and outside source control. Hashes detect changes but are not a substitute for trusted signatures. Device-specific AVB, encryption and anti-rollback rules must be designed and tested before installation support. Do not automatically disable verification or relock a bootloader.

Swir Update, SwirRoot, recovery and SwirPhoneStudio must share a consistent state model so an OTA cannot unknowingly overwrite a rooted/custom boot state and an unroot/restore operation cannot silently break the next verified update path.

## Resource gates

A full AOSP build is a different workload from host unit tests. The checked upstream setup guidance specifies substantial Linux x86-64 build resources; record available disk/RAM and obtain an appropriate build runner before downloading the tree. Do not purchase infrastructure or claim a compiled ROM when only documentation or Python tests exist.
