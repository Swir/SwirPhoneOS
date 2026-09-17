# SwirPhoneStudio device support readiness review

SwirPhoneStudio can review a local `device_support_readiness` schema-v1 report without contacting, rebooting, unlocking, flashing, rooting, erasing or otherwise mutating a phone.

## Purpose

The view makes the gap between a metadata-only device profile and physically verified SwirPhoneOS support visible to the owner. It binds the already-validated readiness report to a small UI-safe projection containing the profile/device identity, current and target builds, missing physical gates, unverified capability status, evidence digest and explicit authorization state.

This is a review surface only. It is not an installer and it cannot promote a device profile.

## Fail-closed file handling

The Studio loader accepts only:

- an absolute path;
- an existing regular `.json` file;
- a non-symlink file no larger than 256 KiB;
- strict UTF-8 JSON without duplicate keys;
- a report that passes the canonical `validate_device_support_readiness()` schema and integrity checks.

The selected path is deliberately not resolved before validation. This preserves the symlink check instead of silently following a link to its target.

## Non-authorizing projection

A successful review still requires all of the following to remain false:

- `support_claim_allowed`;
- `profile_promotion_allowed`;
- `install_allowed`;
- `device_write_allowed`;
- `root_allowed`.

The support state must remain exactly `NOT_SUPPORTED`. Telephony, camera, audio, Wi-Fi, Bluetooth, sensors, GNSS and NFC remain `UNVERIFIED` in schema v1.

The public Studio summary intentionally omits the hardware-evidence and recovery-journal source digests. It exposes the final readiness evidence SHA-256 so an operator can correlate the UI with the exact reviewed report without turning the UI summary into a replacement evidence document.

## Localization

All new user-facing strings are data-only catalog entries for the current SwirPhoneOS host locales:

- English (`en`)
- Polish (`pl`)
- Norwegian Bokmål (`nb`)
- German (`de`)
- Spanish (`es`)
- French (`fr`)
- Portuguese (`pt`)
- Arabic (`ar`)

The shared localization loader requires exact key and placeholder coverage for every registered locale. The Windows packaging spec includes the complete `catalogs.d` directory, so the same review surface is present in the frozen developer executable.

## What is still required for real device support

Schema v1 cannot satisfy the physical gates by design. A later evidence schema must be backed by actual owner-controlled hardware testing and, at minimum, prove:

1. physical device identity and hardware verification;
2. the exact partition map;
3. a tested stock-restore path;
4. SwirPhoneOS boot on the exact device/build;
5. a complete install cycle;
6. a complete rollback cycle;
7. a usable core phone experience;
8. truthful per-device capability results for telephony, camera, audio, radios and sensors.

Until those gates exist and pass, SwirPhoneStudio must continue to display the device as not supported and must not expose an install/root authorization path from this report.
