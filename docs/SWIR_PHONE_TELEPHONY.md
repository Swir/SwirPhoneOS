# Swir Phone Telephony Safety and Validation

Swir Phone is a first-party SwirPhoneOS system application. This document describes the current **source-stage** telephony boundary and the evidence still required before any runtime or device-support claim is allowed.

## Current source-stage scope

The checked-in app currently provides three source-level capabilities:

1. `dialer` — owner-entered numbers are normalized by a dependency-free policy and handed to Android through visible `Intent.ACTION_DIAL`. The app does not request `CALL_PHONE` and does not invoke `TelecomManager.placeCall`.
2. `in_call` — an Android `InCallService` and non-exported in-call activity provide answer/reject/end controls only after the owner has approved Swir Phone as the default dialer. This remains unverified against a real SwirPhoneOS runtime and modem/IMS stack.
3. `recent_calls` — read-only call history requires both the owner-approved default-dialer role and an explicit runtime `READ_CALL_LOG` grant. The source queries at most 20 rows, exposes only a bounded display label, type, localized date/time and duration, and never inserts, updates or deletes call-log data.

All three capabilities remain `ANDROID_SOURCE`, not `ANDROID_RUNTIME` or `HARDWARE_VERIFIED`.

## Permission boundary

The exact reviewed manifest permission set for Swir Phone is:

```text
android.permission.READ_CALL_LOG
```

The source contract rejects permission drift. In particular, these permissions are not allowed:

```text
android.permission.CALL_PHONE
android.permission.WRITE_CALL_LOG
```

Recent-call access is additionally gated in code by the default-dialer role and a runtime permission check. Losing either condition causes the path to fail closed.

## Recent-call privacy model

`CallHistoryPolicy` is pure Java and host-testable. It applies these constraints before call-log values are shown:

- restricted/private presentation never exposes the cached name or number;
- control characters are removed from labels;
- displayed labels are bounded to 80 characters;
- invalid/sentinel negative numbers fall back to the localized unknown-number label;
- history rendering is bounded to 20 entries;
- negative durations clamp to zero and duration formatting is bounded;
- call types are mapped to a closed localized category set.

The Android source uses `CallLog.Calls.NUMBER_PRESENTATION` and exposes a number/name only when presentation is `TelecomManager.PRESENTATION_ALLOWED`.

## Mutation boundary

The reviewed Swir Phone source must not contain:

- `Intent.ACTION_CALL`;
- `TelecomManager.placeCall`;
- `CALL_PHONE`;
- `WRITE_CALL_LOG`;
- call-log `insert`, `update` or `delete` operations;
- arbitrary process execution or root helpers.

Outgoing calls remain a visible Android hand-off. Call history remains read-only. SwirRoot is a separate subsystem and cannot be used to bypass this boundary.

## Localization and layout

Swir Phone currently carries Android resource catalogs for:

- English (`en`)
- Polish (`pl`)
- Norwegian Bokmål (`nb`)
- German (`de`)
- Spanish (`es`)
- French (`fr`)
- Portuguese (`pt`)
- Arabic (`ar`)

The app is RTL-aware. Default-role, active-call and recent-call actions are vertically stacked so translated labels have a full-width touch target instead of competing for a three-column row. Runtime visual review, text expansion and Arabic RTL review still require a real booted image.

## CI and source gates

Host/source validation covers:

- exact permission allowlist;
- visible `ACTION_DIAL` hand-off;
- default-dialer role request;
- `READ_CALL_LOG` role/permission ordering;
- read-only call-log query and bounded result count;
- restricted-number privacy behavior;
- pure-Java dial and call-history policies;
- exact staging into the AOSP product;
- localization-key parity across all eight current locales;
- rejection of direct-call and call-log-write regressions.

Passing these checks proves only that the reviewed source contract is internally consistent. It does not prove that Android grants the role/permission correctly in SwirPhoneOS, that telephony works, or that the app behaves correctly on physical hardware.

## Runtime gate

Before `phone` can be reviewed for `ANDROID_RUNTIME`, the exact pinned SwirPhoneOS image must build and boot, and the same runtime evidence chain must show the package installed and launchable. Focused owner-visible tests must then verify at least:

- default-dialer role request, acceptance and denial;
- `READ_CALL_LOG` denial, grant and revoke behavior;
- empty and populated recent-call lists;
- private/restricted caller presentation remains hidden;
- locale-specific date/time and type labels;
- in-call answer/reject/end controls against Android Telecom in the emulator where supported;
- no direct outgoing-call path appears after integration;
- accessibility, text expansion and RTL behavior.

Automated source tests do not satisfy this gate.

## Physical-device gate

Reference-hardware credit requires separate evidence on the exact supported device/build. For telephony, that includes the supported SIM/modem/IMS/carrier configuration and documented results for incoming/outgoing calls, caller identity, call history, audio routing and relevant emergency-call limitations. Any unsupported feature or carrier condition must be disclosed per device/build.

The planned `oneplus/avicii` profile remains `PLANNED_NOT_SUPPORTED`. No current Swir Phone source work changes that status.

## Progress accounting

This source-stage telephony work does not complete an engineering milestone by itself. The canonical weighted project ledger remains authoritative, and source-only capability coverage cannot satisfy AOSP build, emulator boot, reference hardware, install/recovery or beta gates.
