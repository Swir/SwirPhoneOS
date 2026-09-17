# SwirPhoneOS System Apps

SwirPhoneOS is intended to be a complete everyday mobile operating system, not only a bootable image. It therefore owns a coherent first-party application suite and one original design language.

An app is not considered implemented merely because a package, screen or static mockup exists. Registry states deliberately distinguish planning/host contracts, checked-in Android source, Android runtime evidence and physical-device verification.

## Status model

- `HOST_CONTRACT` — product/API requirements exist; no Android source claim.
- `ANDROID_SOURCE` — meaningful Android source is checked in and source-level validation exists, but no Android build/runtime claim is allowed.
- `ANDROID_RUNTIME` — the app has been built into the pinned SwirPhoneOS product and exercised in the target Android runtime.
- `HARDWARE_VERIFIED` — hardware-dependent capability has also passed exact-device evidence.

The current registry contains 20 apps: **0 `HOST_CONTRACT`, 20 `ANDROID_SOURCE`, 0 `ANDROID_RUNTIME`, 0 `HARDWARE_VERIFIED`.** Source breadth is complete; runtime and hardware readiness are not.

## Source-ready apps

### Swir Phone
Permission-free owner-visible keypad with host-tested fail-closed dial normalization and `ACTION_DIAL` hand-off. It does not request `CALL_PHONE`, place calls directly or read the call log. `in_call` and `recent_calls` remain open.

### Swir Contacts
Requests exactly `READ_CONTACTS`, browses/searches ContactsProvider, delegates create/edit to Android and provides explicit vCard import/export. It has no `WRITE_CONTACTS`, storage or network permission.

### Swir Messages
Permission-free local composer with private draft persistence, bounded recipients/body and `ACTION_SENDTO` + `smsto:` hand-off. It does not silently send/read SMS. MMS and conversation history remain open.

### Swir Camera
Permission-free Camera2 capability inspector that enumerates cameras, facing and largest JPEG output size. Photo/video buttons hand off to Android's visible capture surface. Direct Camera2 capture, camera permission ownership and exact-device photo/video validation remain open, so `photo_capture` and `video_capture` are not claimed.

### Swir Gallery
Requests exactly `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`, browses scoped MediaStore content, supports search/open/share and delegates deletion to Android's owner-confirmed flow. Albums remain open.

### Swir Files
Permission-free file manager using an owner-selected Storage Access Framework tree. It supports browse/search/create/rename/copy/move/delete/open/share without broad storage access.

### Swir Settings
Beta-critical permission-free settings hub with localized search, real build/device status and an exact reviewed allowlist of Android settings routes.

### Swir Browser
Requests exactly `INTERNET`. The WebView path is HTTPS-only, disables cleartext/file/content access, starts with JavaScript and DOM storage disabled, blocks third-party cookies, enables Safe Browsing and provides explicit local browsing-data clearing. Owner opt-in can enable JavaScript for the current session. Downloads remain open.

### Swir Clock
Permission-free locale-formatted clock with foreground stopwatch/timer and owner-visible Android alarm hand-off. It does not request exact-alarm privileges.

### Swir Calculator
Permission-free BigDecimal basic arithmetic with host-tested policy and locale-aware display. Scientific math remains open.

### Swir Notes
Permission-free private SQLite notes with create/edit/delete/search, explicit sharing and owner-selected Markdown export.

### Swir Recorder
Requests exactly `RECORD_AUDIO`, records AAC/MPEG-4 to app-private storage while foregrounded, supports pause/resume/stop/playback, surfaces microphone mute state and exports through an owner-selected document. Exact-device audio remains unverified.

### Swir Calendar
Permission-free local SQLite agenda with editing/search/share and iCalendar export. CalendarProvider bridging remains open.

### Swir Weather
Requests exactly `INTERNET`. It retrieves bounded current-weather JSON over `HttpsURLConnection` from Open-Meteo using owner-entered latitude/longitude, persists metric/imperial preference and exposes provider attribution. It deliberately does not request device location permission.

### Swir Update
Beta-critical read-only channel/build state plus host-tested SHA-256/RSA metadata verification. Download, staging and recovery install remain disabled; staged update state and recovery hand-off remain open.

### Swir Backup
Permission-free owner-controlled document backup using Storage Access Framework. It creates bounded ZIP-compatible `.swirbackup` archives containing selected documents and build fingerprint/SDK metadata, and performs fail-closed archive inspection with traversal/count/size limits. It cannot read other apps' private data and deliberately does not restore archive entries yet; `restore_orchestration` remains open.

### Swir Privacy
Beta-critical permission-free center that opens only an exact reviewed allowlist of Android privacy/permission surfaces. Live indicators and access history remain open.

### Swir Device Care
Beta-critical permission-free diagnostics backed by Android framework state for device/security patch, battery/charging, storage, memory and thermal status. Exact-hardware interpretation remains provisional.

### Swir Apps
Permission-free local Software Center foundation showing launchable apps, package/version and signing-certificate SHA-256 provenance, with launch and authoritative app-details hand-off. Remote catalog/download/install/update status remains open.

### SwirRoot
Original owner UI plus a non-exported status/diagnostic service, explicit enable/unroot review dialogs, bounded local audit and host-tested fail-closed transition gates. It reports `UNAVAILABLE`, hard-disables the mutation backend and supported-build switch, requests no Android permissions, and contains no `su`, process execution, boot-image mutation, partition write, unlock, flash or exploit path. Guided enable/unroot remain open until an exact physically verified backend and rollback/recovery proof exist.

## Shared source contract

All twenty apps use original SwirPhoneOS icons/UI and Android resources for English, Polish, Norwegian Bokmål, German, Spanish, French, Portuguese and Arabic. Layout direction follows the locale. Localization lint enforces key parity, formatter signatures, plural contracts and common direct Java UI-literal sinks.

Source validation requires package identity, exact least-privilege permission allowlists, product inclusion and complete bounded AOSP staging. Network primitives are reviewed only for Swir Browser and Swir Weather; other apps fail closed on unreviewed network code. Broad-storage and process-execution primitives remain rejected. SwirRoot receives additional hard-disabled mutation checks.

Source-summary schema v3 records missing capabilities by **app + capability**. Important open items include `phone:in_call`, `phone:recent_calls`, `messages:mms`, `messages:conversation_history`, `camera:photo_capture`, `camera:video_capture`, `browser:downloads`, `calendar:provider_bridge`, `backup:restore_orchestration`, `apps:update_status`, `swirroot:guided_enable` and `swirroot:guided_unroot`.

None of the twenty is `ANDROID_RUNTIME` until a real pinned-AOSP build and Cuttlefish exercise succeeds.

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

## Delivery order

### Emulator-ready core

All twenty source-ready apps now need the real AOSP build/runtime gate rather than more package breadth. They must compile into the pinned product, launch in Cuttlefish and pass focused checks for state, persistence, permissions, accessibility, locale switching and RTL. Source-only work receives no weighted progress credit.

### Reference hardware

Bring up exact telephony/default-role behavior for Phone/Messages, direct camera capture, recorder/audio, Gallery media behavior and Backup restore only against a physically verified supported build. Camera photo/video and Backup restore capabilities remain deliberately unpromoted until those tests exist.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency. Add signed Swir Apps update status only when the distribution trust model exists. SwirRoot mutation remains blocked until exact-build recovery evidence exists.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. A real implementation must show authoritative root state, require exact-build support and owner confirmation, verify rollback before mutation, keep a durable operation journal, provide tested unroot/recovery and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when a privileged service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera, recorder/audio and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
