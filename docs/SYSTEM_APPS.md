# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable image. It therefore owns a coherent first-party application suite and one original design language.

An app is not considered implemented merely because a package, screen or static mockup exists. Registry states deliberately distinguish planning/host contracts, checked-in Android source, Android runtime evidence and physical-device verification.

## Status model

- `HOST_CONTRACT` — product/API requirements exist; no Android source claim.
- `ANDROID_SOURCE` — meaningful Android source is checked in and source-level validation exists, but no Android build/runtime claim is allowed.
- `ANDROID_RUNTIME` — the app has been built into the pinned SwirPhoneOS product and exercised in the target Android runtime.
- `HARDWARE_VERIFIED` — hardware-dependent capability has also passed exact-device evidence.

The current registry contains 20 apps: **4 `HOST_CONTRACT`, 16 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`.**

## Source-ready apps

### Swir Phone

Swir Phone is a permission-free source-stage dialer surface with an original SwirPhoneOS keypad, accessibility labels and host-tested fail-closed dial-string policy. It normalizes bounded owner-entered phone strings and uses `Intent.ACTION_DIAL` to transfer the number to Android's authoritative system dialer, where the owner still confirms the call. It does not request `CALL_PHONE`, place calls directly, read the call log or claim default-dialer/in-call functionality. `phone:in_call` and `phone:recent_calls` remain explicitly unfinished until the exact Telecom/telephony stack and reference hardware are validated.

### Swir Messages

Swir Messages is a permission-free source-stage composer with app-private draft persistence, host-tested recipient/body bounds and an explicit `Intent.ACTION_SENDTO` + `smsto:` hand-off to an installed Android messaging app. It never calls `SmsManager`, does not request `SEND_SMS`, `READ_SMS` or `RECEIVE_SMS`, and does not silently send or read messages. `messages:mms` and `messages:conversation_history` remain explicitly unfinished until the exact platform telephony role/provider model and reference hardware are reviewed. The current `sms` source capability means safe owner-visible compose/handoff only; it is not a runtime or carrier-delivery claim.

### SwirCalculator

SwirCalculator contains real AOSP `android_app` source, a pure-Java BigDecimal state machine, basic arithmetic/decimal/sign/percent/backspace/error handling, an original vector icon and dark/cyan SwirPhoneOS UI. It requests no Android permissions. Scientific math remains a target rather than an implemented capability.

### SwirSettings

SwirSettings is a beta-critical permission-free settings hub with localized search, real build/device status and reviewed hand-off routes to authoritative Android settings surfaces. Its pure-Java route catalog is host-tested and source validation requires the exact reviewed action allowlist.

### SwirFiles

SwirFiles is a beta-critical permission-free file manager built around an owner-selected Storage Access Framework tree grant. It browses/searches that tree and uses provider-supported create/rename/copy/move/delete/open/share operations without broad storage permissions. Delete remains confirmation-gated and its pure-Java file policy is host-tested.

### SwirDeviceCare

SwirDeviceCare is a beta-critical permission-free diagnostics source backed by Android framework state for manufacturer/model/security patch, battery/charging, storage, memory and current thermal state. Hardware interpretation remains provisional until exact-device testing.

### SwirUpdate

SwirUpdate is meaningful beta-critical Android source, but deliberately **not an installer yet**. It reports real local build identity and contains a dependency-free SHA-256/RSA detached-signature verification policy. No network permission, downloader, update-package staging, recovery install or silent write path is present. `staged_update_state` and `recovery_handoff` remain future capabilities.

### SwirPrivacy

SwirPrivacy is a beta-critical permission-free privacy center. It searches and opens only an exact reviewed allowlist of Android privacy, permission, location, app and special-access settings. Platform-backed live privacy indicators and access history remain future work.

### SwirClock

SwirClock is a permission-free daily clock source with locale-formatted time/date, foreground stopwatch/timer and a user-visible hand-off to Android alarm creation. It does not request exact-alarm privileges or silently create alarms.

### SwirNotes

SwirNotes stores owner-created notes in an app-private SQLite database and supports create/edit/delete/search, explicit text sharing and user-selected Markdown export. It requests no network or storage permission.

### SwirCalendar

SwirCalendar stores a local SQLite agenda, supports date/time editing and search, and provides explicit sharing plus user-selected iCalendar export. CalendarProvider integration remains unimplemented and is tracked specifically as `calendar:provider_bridge`.

### SwirGallery

SwirGallery requests exactly `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`, browses scoped MediaStore content, supports local search/open/share and delegates deletion to Android's owner-confirmed flow. Album grouping remains a future capability.

### SwirRecorder

SwirRecorder requests exactly `RECORD_AUDIO`, records AAC/MPEG-4 to app-private storage while foregrounded, supports pause/resume/stop/playback, surfaces microphone-mute state and exports through a user-selected document. Exact-device audio behavior remains unverified.

### SwirContacts

SwirContacts is a real local ContactsProvider client rather than a placeholder list. It requests exactly `READ_CONTACTS`, browses names and phone numbers through the Android provider, supports local search, and hands creation/editing to Android's authoritative contact UI. Import is an explicit user-selected vCard hand-off and export copies the selected provider vCard to a user-selected document. It deliberately does not request `WRITE_CONTACTS`, storage or network permissions. Its pure-Java `ContactPolicy` is host-tested for search, lookup-key validation and safe export naming.

### Swir Apps

Swir Apps is a permission-free local Software Center foundation. It enumerates visible launchable apps through PackageManager, displays package/version state, derives a bounded SHA-256 signing-certificate fingerprint, launches selected apps and opens Android's authoritative application-details surface. It has no remote catalog, downloader or installer and therefore does not claim `update_status`; that remains tracked as `apps:update_status`. Its pure-Java `AppCatalogPolicy` validates package identities, search and signer-digest formatting.

### SwirRoot

SwirRoot provides an original SwirPhoneOS owner UI, current build fingerprint, explicit root-state vocabulary, owner-confirmed enable/unroot **review** dialogs, a non-exported status/diagnostic service, bounded app-private workflow audit and host-tested safety gates.

The current source is intentionally fail-closed. It reports `UNAVAILABLE`, hard-disables its mutation backend and supported-build switch, requests no Android permissions and contains no process execution, boot-image modification, partition write, bootloader unlock, flash or exploit/bypass path. `guided_enable` and `guided_unroot` remain future capabilities until a legitimate exact-build backend and physical rollback/recovery proof exist.

All sixteen source-ready apps use original SwirPhoneOS icons/UI and Android resources for English, Polish, Norwegian Bokmål, German, Spanish, French, Portuguese and Arabic. Layout direction follows the locale. Source validation checks package identity, exact per-app permission allowlists, localization-key/formatter/plural parity, product inclusion and complete bounded AOSP staging. It scans production Java for forbidden execution/network/broad-storage primitives and applies additional fail-closed constraints to SwirRoot.

Source-summary schema v3 records missing capabilities by **app + capability**, not just capability name. This avoids false completion when multiple apps use the same capability label: SwirContacts can implement its provider bridge while Calendar's provider bridge remains open; Swir Phone can implement its dialer hand-off while `phone:in_call` and `phone:recent_calls` remain open; and Swir Messages can implement safe SMS compose/handoff while `messages:mms` and `messages:conversation_history` remain open.

None of the sixteen is `ANDROID_RUNTIME` until a real pinned-AOSP build and Cuttlefish exercise succeeds.

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

Phone/SMS/Camera and other hardware-backed functions are declared only after validation against the exact reference-device stack. Swir Phone can provide a source-ready keypad and user-visible dialer hand-off before telephony validation, but in-call/default-dialer/recent-call behavior remains unimplemented and unverified. Swir Messages can provide a safe source-ready composer and owner-visible send hand-off before telephony validation, but default-SMS role, message-provider history, MMS and carrier delivery remain unimplemented/unverified. Contacts can have meaningful provider-backed source before telephony validation, but its runtime behavior remains unverified until the built product is exercised.

## Delivery order

### Emulator-ready core

Prioritize the current sixteen source-ready apps through the real AOSP build and Cuttlefish runtime gate before adding more package breadth. All sixteen must build, launch and pass focused checks for state, persistence, permission handling, accessibility, locale switching and RTL. Source-only additions do not receive weighted progress credit.

### Reference hardware

Bring up the remaining Swir Phone telephony role/in-call/recent-call behavior, Swir Messages default-role/provider/MMS behavior, Camera and Backup as telephony, audio, camera, storage, sensors, power and encryption become validated for the reference device. Validate Contacts provider behavior, Recorder audio and Gallery media behavior on the same supported build before making physical-device claims.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency. Add a reviewed signed source for Swir Apps update status only when the OTA/app distribution trust model exists. SwirRoot mutation remains blocked until exact-build recovery evidence exists.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. Its source-stage UI/service now exists, but executable root support does not. A real implementation must show authoritative root state, require explicit exact-build support and owner confirmation, verify rollback material before mutation, keep a durable operation journal, provide tested unroot/recovery, and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when a privileged service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera, recorder/audio and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
