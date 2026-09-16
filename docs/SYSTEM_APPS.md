# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable image. It therefore owns a coherent first-party application suite and one original design language.

An app is not considered implemented merely because a package, screen or static mockup exists. Registry states deliberately distinguish planning/host contracts, checked-in Android source, Android runtime evidence and physical-device verification.

## Status model

- `HOST_CONTRACT` — product/API requirements exist; no Android source claim.
- `ANDROID_SOURCE` — meaningful Android source is checked in and source-level validation exists, but no Android build/runtime claim is allowed.
- `ANDROID_RUNTIME` — the app has been built into the pinned SwirPhoneOS product and exercised in the target Android runtime.
- `HARDWARE_VERIFIED` — hardware-dependent capability has also passed exact-device evidence.

The current registry contains 20 apps: **19 `HOST_CONTRACT`, 1 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`.**

## First source-ready app: SwirCalculator

SwirCalculator is the first application at `ANDROID_SOURCE`. It contains real AOSP `android_app` source, a pure-Java BigDecimal state machine, basic arithmetic/decimal/sign/percent/backspace/error handling, an original vector icon and dark/cyan SwirPhoneOS UI. It requests no Android permissions. Source checks reject network/process/root primitives, package drift, localization-key drift and incomplete staging.

Android string resources currently cover English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Layout direction follows the locale and the UI exposes accessibility descriptions. Scientific-math functionality remains a target rather than an implemented capability. No APK/Cuttlefish claim is made until the pinned AOSP product actually builds and the app is launched/tested there.

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

Prioritize Swir Settings, Files, Update, Privacy, Device Care, Clock and Calculator. Source can be developed in parallel, but runtime completion requires a real SwirPhoneOS Cuttlefish build/boot.

### Reference hardware

Bring up Phone, Contacts, Messages, Camera, Gallery, Recorder, Backup and hardware-backed Device Care as telephony, audio, camera, storage, sensors, power and encryption become validated for the reference device.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. It must show authoritative root state, require explicit exact-build support and owner confirmation, verify rollback material before mutation, keep an operation journal, provide tested unroot/recovery, and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when the service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
