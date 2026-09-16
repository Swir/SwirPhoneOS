# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable image. It therefore owns a coherent first-party application suite and one original design language.

An app is not considered implemented merely because a package, screen or static mockup exists. Registry states deliberately distinguish planning/host contracts, checked-in Android source, Android runtime evidence and physical-device verification.

## Status model

- `HOST_CONTRACT` — product/API requirements exist; no Android source claim.
- `ANDROID_SOURCE` — meaningful Android source is checked in and source-level validation exists, but no Android build/runtime claim is allowed.
- `ANDROID_RUNTIME` — the app has been built into the pinned SwirPhoneOS product and exercised in the target Android runtime.
- `HARDWARE_VERIFIED` — hardware-dependent capability has also passed exact-device evidence.

The current registry contains 20 apps: **14 `HOST_CONTRACT`, 6 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`.**

## Source-ready apps

### SwirCalculator

SwirCalculator contains real AOSP `android_app` source, a pure-Java BigDecimal state machine, basic arithmetic/decimal/sign/percent/backspace/error handling, an original vector icon and dark/cyan SwirPhoneOS UI. It requests no Android permissions. Scientific math remains a target rather than an implemented capability.

### SwirSettings

SwirSettings is a beta-critical permission-free settings hub with localized search, real build/device status and reviewed hand-off routes to authoritative Android settings surfaces. Its pure-Java route catalog is host-tested and source validation requires the exact reviewed action allowlist.

### SwirFiles

SwirFiles is a beta-critical permission-free file manager built around an owner-selected Storage Access Framework tree grant. It browses/searches that tree and uses provider-supported create/rename/copy/move/delete/open/share operations without broad storage permissions. Delete remains confirmation-gated and its pure-Java file policy is host-tested.

### SwirDeviceCare

SwirDeviceCare is a beta-critical permission-free diagnostics source backed by Android framework state for manufacturer/model/security patch, battery/charging, storage, memory and current thermal state. A pure-Java health model is host-tested. Hardware interpretation remains provisional until exact-device testing.

### SwirUpdate

SwirUpdate is now meaningful beta-critical Android source, but deliberately **not an installer yet**. It reports real local build identity, maps build type/tags to a visible development channel, and contains a dependency-free SHA-256/RSA detached-signature verification policy with host tests including tamper rejection. It exposes a safe hand-off to Android's existing system-update settings where available.

No network permission, downloader, update-package staging, recovery install or silent write path is present. `staged_update_state` and `recovery_handoff` remain unimplemented target capabilities until the signed OTA/recovery architecture is built and runtime-tested.

### SwirPrivacy

SwirPrivacy is a beta-critical permission-free privacy center. It searches and opens only an exact reviewed allowlist of authoritative Android privacy, permission, location, app and special-access settings. The pure-Java route catalog is host-tested and unreviewed routes fail source validation.

At this stage the implemented capability is `permission_review`. Platform-backed live privacy indicators and access history remain explicit future work rather than placeholder claims.

All six source-ready apps use original SwirPhoneOS icons/UI and Android resources for English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Layout direction follows the locale. Source validation checks package identity, permission boundaries, localization-key parity, product inclusion and complete bounded AOSP staging. None is `ANDROID_RUNTIME` until a real pinned-AOSP build and Cuttlefish exercise succeeds.

## Design principles

- Shared SwirPhoneOS typography, spacing, motion, surfaces, icons and navigation.
- Original visual identity rather than copying Pixel, One UI, HyperOS, Magisk or another product.
- Responsive phone layouts, scalable text, meaningful accessibility semantics and useful touch targets.
- System-language startup, English fallback and data/resource-driven localization.
- RTL-aware layouts plus locale-specific date/time/number/unit formatting where applicable.
- Dark/light presentation where appropriate, with a distinctive SwirPhoneOS dark/neon identity.
- Offline-capable core functions whenever the feature itself does not require a network service.
- Clear permission/privacy/diagnostic surfaces instead of hidden behavior.
- A dedicated SwirPhoneOS icon for every app.

## Essential suite

**Communication:** Swir Phone, Contacts, Messages.

**Media/capture:** Swir Camera, Gallery, Recorder.

**Daily tools:** Swir Files, Browser, Clock, Calculator, Notes, Calendar, Weather.

**System/trust:** Swir Settings, Update, Backup, Privacy, Device Care, Apps/Software Center and SwirRoot.

Phone/SMS/Camera/Recorder and other hardware-backed functions are declared only after validation against the exact reference-device stack.

## Delivery order

### Emulator-ready core

Prioritize Swir Settings, Files, Update, Privacy, Device Care, Clock and Calculator. Calculator, Settings, Files, Device Care, Update and Privacy now have meaningful Android source, but runtime completion still requires a real SwirPhoneOS Cuttlefish build/boot. Clock remains the next daily-use core app candidate while Update/Privacy need platform integration after runtime surfaces exist.

### Reference hardware

Bring up Phone, Contacts, Messages, Camera, Gallery, Recorder, Backup and hardware-backed Device Care as telephony, audio, camera, storage, sensors, power and encryption become validated for the reference device.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. It must show authoritative root state, require explicit exact-build support and owner confirmation, verify rollback material before mutation, keep an operation journal, provide tested unroot/recovery, and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when the service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
