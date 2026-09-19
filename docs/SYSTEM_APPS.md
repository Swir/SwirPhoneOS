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
Owner-visible keypad with host-tested fail-closed dial normalization and explicit `ACTION_DIAL` hand-off. The owner may request Android's default-dialer role; source-stage in-call answer/reject/end controls are available only through that role. Recent-call history is bounded to 20 entries, requires both the default-dialer role and explicit runtime `READ_CALL_LOG`, hides restricted/private presentation, and queries the call log read-only. Swir Phone does not request `CALL_PHONE` or `WRITE_CALL_LOG`, place outgoing calls directly, or insert/update/delete call-log rows. Real Telecom/modem/IMS and device behavior remain runtime- and hardware-unverified.

### Swir Contacts
Requests exactly `READ_CONTACTS`, browses/searches ContactsProvider, delegates create/edit to Android and provides explicit vCard import/export. It has no `WRITE_CONTACTS`, storage or network permission.

### Swir Messages
Permission-free local composer with private draft persistence, bounded recipients/body and `ACTION_SENDTO` + `smsto:` hand-off. It does not silently send/read SMS. MMS and conversation history remain open.

### Swir Camera
Permission-free Camera2 capability inspector that enumerates cameras, facing and largest JPEG output size. Photo/video buttons hand off to Android's visible capture surface. Direct Camera2 capture, camera permission ownership and exact-device photo/video validation remain open, so `photo_capture` and `video_capture` are not claimed.

### Swir Gallery
Requests exactly `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`, browses scoped MediaStore content, supports search/open/share, groups granted media by bounded MediaStore bucket metadata for local album filtering and delegates deletion to Android's owner-confirmed flow. Album behavior is source-implemented but remains Android-runtime/provider unverified.

### Swir Files
Permission-free file manager using an owner-selected Storage Access Framework tree. It supports browse/search/create/rename/copy/move/delete/open/share without broad storage access.

### Swir Settings
Beta-critical permission-free settings hub with localized search, real build/device status and an exact reviewed allowlist of Android settings routes.

### Swir Browser
Requests exactly `INTERNET`. The WebView path is HTTPS-only, disables cleartext/file/content access, starts with JavaScript and DOM storage disabled, blocks third-party cookies, enables Safe Browsing and provides explicit local browsing-data clearing. Owner opt-in can enable JavaScript for the current session. Downloads are source-implemented through app-scoped, owner-visible `DownloadManager` handling; runtime redirect/provider behavior remains unverified.

### Swir Clock
Permission-free locale-formatted clock with foreground stopwatch/timer and owner-visible Android alarm hand-off. It does not request exact-alarm privileges.

### Swir Calculator
Permission-free BigDecimal arithmetic with host-tested source-stage scientific functions/keypad, DEG/RAD handling and locale-aware display. Source capability accounting includes both `basic_math` and `scientific_math`; Android runtime and visual/accessibility review remain open.

### Swir Notes
Permission-free private SQLite notes with create/edit/delete/search, explicit sharing and owner-selected Markdown export.

### Swir Recorder
Requests exactly `RECORD_AUDIO`, records AAC/MPEG-4 to app-private storage while foregrounded, supports pause/resume/stop/playback, surfaces microphone mute state and exports through an owner-selected document. Exact-device audio remains unverified.

### Swir Calendar
Permission-free local SQLite agenda with editing/search/share, bounded owner-selected iCalendar import/export and an owner-visible Android calendar insert hand-off. It does not request direct calendar read/write permission; provider runtime behavior remains unverified.

### Swir Weather
Requests exactly `INTERNET`. It retrieves bounded current-weather JSON over `HttpsURLConnection` from Open-Meteo using owner-entered latitude/longitude, persists metric/imperial preference and exposes provider attribution. It deliberately does not request device location permission.

### Swir Update
Beta-critical read-only channel/build state plus host-tested SHA-256/RSA metadata verification and fail-closed OTA trust-store/source policy. Download, staging and recovery install remain disabled; staged update state and recovery hand-off remain open.

### Swir Backup
Permission-free owner-controlled document backup using Storage Access Framework. It creates bounded schema-v2 `.swirbackup` archives containing selected documents and build metadata, binds every file to SHA-256, rechecks source bytes before archive write, performs strict archive inspection and restores only into an explicitly owner-selected SAF tree. Legacy schema-v1 archives remain inspect-only. This does not read private app data or partitions and does not satisfy broader device/recovery `restore_orchestration`.

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

Source validation requires package identity, exact least-privilege permission allowlists, product inclusion and complete bounded AOSP staging. Swir Phone is allowed only `READ_CALL_LOG`; Contacts only `READ_CONTACTS`; Gallery only `READ_MEDIA_IMAGES` + `READ_MEDIA_VIDEO`; Recorder only `RECORD_AUDIO`; Browser and Weather only `INTERNET`. The remaining source apps are permission-free. Network primitives are reviewed only for Swir Browser and Swir Weather; other apps fail closed on unreviewed network code. Broad-storage and process-execution primitives remain rejected. Swir Phone additionally rejects direct-call and call-log-write primitives, and SwirRoot receives additional hard-disabled mutation checks.

Source-summary schema v3 records missing capabilities by **app + capability**. Swir Phone `dialer`, `in_call` and bounded read-only `recent_calls`, Swir Gallery `albums`, and Swir Calculator `scientific_math` are source-implemented. Important open items include `messages:mms`, `messages:conversation_history`, `camera:photo_capture`, `camera:video_capture`, `backup:restore_orchestration`, `privacy:privacy_indicators`, `privacy:access_history`, `update:staged_update_state`, `update:recovery_handoff`, `apps:update_status`, `swirroot:guided_enable` and `swirroot:guided_unroot`.

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

All twenty source-ready apps now need the real AOSP build/runtime gate rather than more package breadth. They must compile into the pinned product, launch in Cuttlefish and pass focused checks for state, persistence, permissions, accessibility, locale switching and RTL. Swir Phone specifically needs runtime review of default-role acquisition, `READ_CALL_LOG` deny/grant behavior, restricted-number presentation, recent-call rendering and in-call controls. Source-only work receives no weighted progress credit.

### Reference hardware

Bring up exact telephony/default-role/recent-call behavior for Phone and exact default-role/provider/MMS/carrier behavior for Messages; validate Contacts provider behavior on the same physical build. Direct camera capture, recorder/audio, Gallery media behavior and Backup recovery semantics also require a physically verified supported build. Source-stage recent calls do not satisfy telephony or hardware gates.

### Beta integration

Polish cross-app navigation, sharing, search, notifications, permissions, accessibility, localization, crash handling, backup/recovery, app/update signing and visual consistency. Add signed Swir Apps update status only when the distribution trust model exists. SwirRoot mutation remains blocked until exact-build recovery evidence exists.

## SwirRoot

SwirRoot is a first-party owner-controlled root manager, not a bootloader exploit tool and not a Magisk clone. A real implementation must show authoritative root state, require exact-build support and owner confirmation, verify rollback before mutation, keep a durable operation journal, provide tested unroot/recovery and integrate with Update/recovery/SwirPhoneStudio. Per-app root is deny-by-default and auditable when a privileged service exists. Locked bootloaders and OEM protections are never bypassed through exploits.

## Beta policy

A beta requires a coherent usable core plus accurate device-specific limitations. At minimum Settings, Files, update/recovery status and device diagnostics must be functional, and recovery from failure must be possible. Telephony, camera, recorder/audio and SwirRoot are declared per exact tested device/build. App source alone never increases the global weighted percentage.
