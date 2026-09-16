# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable Android image. The operating system therefore owns a coherent first-party system-app suite and a shared design language.

This document defines product scope. An app is not considered implemented merely because a package, screen or static mockup exists. Completion requires usable functionality appropriate to the current platform stage plus integration and tests where practical.

## Design principles

All first-party apps should feel unmistakably like SwirPhoneOS while remaining fast and simple to use.

- One shared SwirPhoneOS design system: typography, spacing, motion, surfaces, icons and navigation.
- Original visual identity rather than copying Pixel, Samsung One UI, MIUI/HyperOS, Magisk or another product.
- Responsive layouts for different phone sizes and orientations.
- Accessibility-first semantics, scalable text and touch targets.
- System-language startup with English fallback and an extensible translation architecture.
- Dark and light presentation where appropriate, with a distinctive SwirPhoneOS dark/neon identity.
- Offline-capable core functions whenever the feature itself does not require a network service.
- Clear permission requests, privacy surfaces and diagnostics instead of hidden background behavior.
- Every app receives its own SwirPhoneOS icon and integrates with common system components instead of duplicating platform logic.

## Essential first-party suite

### Communication

- **Swir Phone** — dialer, in-call surface, recent calls, voicemail integration where the carrier/device stack supports it, emergency-call behavior inherited from the validated telephony platform.
- **Swir Contacts** — local contacts, import/export and account-provider integration when available.
- **Swir Messages** — SMS/MMS first; richer messaging features may be added only when a dependable service path exists.

### Media and capture

- **Swir Camera** — photo/video capture through the validated Android camera stack. Capability is device-profile dependent and must never be claimed before hardware testing.
- **Swir Gallery** — local photos/videos, metadata, albums, share/edit entry points and safe deletion/recovery behavior.
- **Swir Recorder** — voice/audio recording with clear microphone state and file management integration.

### Daily tools

- **Swir Files** — local storage browser, search, copy/move/rename/share, storage-provider integration and safe destructive actions.
- **Swir Browser** — standards-based web browsing using an auditable maintained engine rather than a custom insecure web engine.
- **Swir Clock** — alarms, timers, stopwatch and world clock.
- **Swir Calculator** — basic and scientific calculation modes.
- **Swir Notes** — fast offline notes with export/share and future optional sync adapters.
- **Swir Calendar** — local calendar plus provider integration when configured.
- **Swir Weather** — optional network-backed weather surface with transparent provider attribution/configuration.

### System control and trust

- **Swir Settings** — authoritative user-facing system configuration, search and device-status surfaces.
- **Swir Update** — signed OTA/update metadata, staged update status, rollback/recovery hand-off and release-channel controls.
- **Swir Backup** — local backup/restore orchestration for supported data and device-specific recovery metadata. It must not promise impossible full backups on unsupported hardware.
- **Swir Privacy** — permissions, privacy indicators, app access review and security-relevant system status.
- **Swir Device Care** — storage, battery, thermal, hardware and service diagnostics based on validated platform APIs.
- **Swir Apps** — first-party software/app center and package-management front end. Source trust, signatures and update provenance must be visible; no silent unknown-source installation.
- **SwirRoot** — owner-controlled root manager for supported SwirPhoneOS device profiles.

## SwirRoot

SwirRoot is a first-party system component, not a bootloader exploit tool and not a Magisk clone.

### Product goals

- Show an unambiguous `ROOT OFF`, `ROOT ON` or `UNAVAILABLE` state.
- Provide a guided enable-root flow only when the current build/device profile explicitly supports it.
- Provide a guided unroot flow that restores the expected non-root boot/system state for the exact build/profile.
- Create and verify required rollback material before enabling root.
- Keep a durable operation journal and useful diagnostics.
- Integrate root state with Swir Update, recovery and SwirPhoneStudio so an OTA or restore cannot silently invalidate the expected state.
- Require explicit owner confirmation for state-changing operations.
- Never bypass a locked bootloader, OEM protection or platform security control through an exploit.

### Future permission manager

When the underlying root service is implemented, SwirRoot should expose per-app root authorization with deny-by-default behavior, explicit grants, revocation, timestamps/audit history and an emergency global disable path. Root must not automatically imply unrestricted background access for every installed app.

## Delivery order

The app suite is developed alongside the platform rather than after it.

### Stage A — pre-boot/platform foundation

Define the common app design system, icon rules, localization structure, package naming, permission conventions, shared settings contracts and test strategy. Build non-hardware-dependent prototypes only where they can later become real platform code.

### Stage B — emulator-ready core

Prioritize **Swir Settings**, **Swir Files**, **Swir Update**, **Swir Privacy**, **Swir Device Care**, Clock and Calculator because they can be exercised meaningfully on the emulator and are required for a usable developer image.

### Stage C — reference hardware

Bring up **Phone**, **Contacts**, **Messages**, **Camera**, Gallery, Recorder, Backup and hardware-backed Device Care functionality as the reference device gains validated telephony, audio, camera, storage, sensors, power and encryption support.

### Stage D — beta-quality integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery interaction, app/update signing and visual consistency. SwirRoot may be enabled only on profiles where enable, disable and recovery paths have been physically verified.

## Beta policy

A beta does not require every future app feature to be complete, but it must provide a coherent usable core and must accurately disclose hardware-dependent limitations. At minimum the beta candidate must have functional Settings, Files, update/recovery status, diagnostics/device basics and the system surfaces required to recover from failure. Telephony, camera and SwirRoot capability are declared per exact supported device/build, never globally.

No app-only mockup increases the global completion percentage. Roadmap credit follows the verified engineering gates in `ROADMAP.md` and `project.json`.
