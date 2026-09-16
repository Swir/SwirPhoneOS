# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable image. It therefore owns a coherent first-party application suite and one original design language.

An app is not considered implemented merely because a package, screen or static mockup exists. Registry states deliberately distinguish planning/host contracts, checked-in Android source, Android runtime evidence and physical-device verification.

## Status model

- `HOST_CONTRACT` — product/API requirements exist; no Android source claim.
- `ANDROID_SOURCE` — meaningful Android source is checked in and source-level validation exists, but no Android build/runtime claim is allowed.
- `ANDROID_RUNTIME` — the app has been built into the pinned SwirPhoneOS product and exercised in the target Android runtime.
- `HARDWARE_VERIFIED` — hardware-dependent capability has also passed exact-device evidence.

The current registry contains 20 apps: **16 `HOST_CONTRACT`, 4 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`.**

## Source-ready apps

### SwirCalculator

SwirCalculator contains real AOSP `android_app` source, a pure-Java BigDecimal state machine, basic arithmetic/decimal/sign/percent/backspace/error handling, an original vector icon and dark/cyan SwirPhoneOS UI. It requests no Android permissions. Source checks reject network/process/root primitives, package drift, localization-key drift and incomplete staging.

Android string resources currently cover English, Polish, Norwegian Bokmal, German, Spanish, French, Portuguese and Arabic. Layout direction follows the locale and the UI exposes accessibility descriptions. Scientific-math functionality remains a target rather than an implemented capability. No APK/Cuttlefish claim is made until the pinned AOSP product actually builds and the app is launched/tested there.

### SwirSettings

SwirSettings is a beta-critical app at `ANDROID_SOURCE`. It is a permission-free settings hub with an original SwirPhoneOS icon and dark/cyan UI, localized search, real `Build.MODEL` / Android version / API status and reviewed hand-off routes to authoritative Android settings pages for Wi-Fi, Bluetooth, display, sound, security, privacy, accessibility, language/region, storage and apps.

The app does not silently mutate platform settings and requests no permissions. Its route catalog is pure Java and host-tested; source validation requires the exact reviewed `android.settings.*` action allowlist and rejects unreviewed settings routes. It ships the same EN/PL/NB/DE/ES/FR/PT/AR resource set and follows locale layout direction. It remains source-only until a pinned AOSP build and Cuttlefish runtime test prove the integration.

### SwirFiles

SwirFiles is a beta-critical permission-free file manager source. It uses `ACTION_OPEN_DOCUMENT_TREE` and a persisted owner-selected Storage Access Framework grant instead of broad storage permissions. Inside that granted tree it browses/searches documents, creates folders and uses provider-advertised rename/copy/move/delete operations. File deletion is confirmation-gated; open/share operations pass only URI grants needed by the receiving app. A pure-Java `FilePolicy` validates names and search behavior in host CI.

The app has an original folder icon/UI, follows locale layout direction and includes EN/PL/NB/DE/ES/FR/PT/AR resources. Source validation rejects broad storage-permission primitives, missing user-granted tree flow, localization drift and incomplete AOSP staging. Runtime behavior remains unverified until a real SwirPhoneOS Cuttlefish build is available.

### SwirDeviceCare

SwirDeviceCare is a beta-critical diagnostics source that intentionally avoids privileged permissions. It renders real Android framework state for manufacturer/model/security patch, battery level and charging state, data-partition storage, memory availability and current thermal condition. A pure-Java `HealthModel` maps usage and thermal state and is dependency-free host tested.

The dashboard has an original SwirPhoneOS shield icon/UI and the same eight locale resource sets. Hardware-dependent interpretation remains provisional: source status proves only the code contract, not the accuracy of a vendor's sensors or charging stack. Physical-device verification is still required before any hardware support claim.

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

Prioritize Swir Settings, Files, Update, Privacy, Device Care, Clock and Calculator. Calculator, Settings, Files and Device Care now have meaningful Android source, but runtime completion still requires a real SwirPhoneOS Cuttlefish build/boot. Continue moving Update and Privacy from host contracts into real source without overstating runtime status.

### Reference hardware

Bring up Phone, Contacts, Messages, Camera, Gallery, Recorder, Backup and hardware-backed Device Care as telephony, audio, camera, storage, sensors, power and encryption become validated for the reference device.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. It must show authoritative root state, require explicit exact-build support and owner confirmation, verify rollback material before mutation, keep an operation journal, provide tested unroot/recovery, and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when the service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
