# Swir Update local package preflight

Swir Update can inspect an owner-selected local OTA candidate without staging or installing it. This is a source-stage safety surface for future update work, not an OTA installer and not release-readiness evidence.

## Current verified behavior

The owner explicitly selects a document through Android's Storage Access Framework (`ACTION_OPEN_DOCUMENT`, `CATEGORY_OPENABLE`, MIME `application/zip`). Swir Update requests no storage or network permission for this flow and opens only the returned content URI for reading.

The dependency-free `UpdatePolicy.inspectPackage(...)` performs a bounded byte-identity preflight:

- requires a simple `.zip` display name with no path separators or control characters;
- rejects an explicitly empty package and rejects declared or observed content above the 16 GiB hard ceiling;
- streams the selected bytes rather than copying them into SwirPhoneOS-managed storage;
- rejects a provider-reported size that differs from the number of bytes actually read;
- requires the ZIP local-file header (`PK 03 04`);
- computes SHA-256 over the exact bytes read;
- reports `REVIEW_READY_UNTRUSTED` only after those local checks succeed.

The UI exposes the state, package name, locale-formatted size and SHA-256 in all current Android locales: EN, PL, NB, DE, ES, FR, PT and AR.

## Deliberately not implemented

`REVIEW_READY_UNTRUSTED` is not an authorization state. The current preflight does **not**:

- authenticate release metadata or bind a trusted signing key to the selected archive;
- prove that the archive targets the current SwirPhoneOS build, device profile, slot or partition topology;
- download an OTA package in the background;
- copy, stage, install, flash, reboot or hand anything to recovery;
- modify `/data`, boot/system/vendor partitions or any device state;
- advance `staged_update_state`, `recovery_handoff`, a weighted engineering milestone or a beta gate.

The existing detached SHA-256/RSA metadata verifier remains a separate primitive. It is not yet connected to a production update manifest/key-rotation policy, so local package SHA-256 alone must never be presented as proof of an authentic SwirPhoneOS update.

## Fail-closed constraints

The Android source contract continues to reject `DownloadManager` and `RecoverySystem.installPackage` in Swir Update. Dedicated regression coverage additionally requires the owner-selected read-only SAF path, no new manifest permission, the bounded size/SHA-256 checks, complete localization key parity and explicit UI language that staging/recovery remain disabled.

A read error, unsafe name, size mismatch/overflow or non-ZIP header produces a rejected/read-failed state and no digest-based trust promotion.

## Required next integration before staging

Before `staged_update_state` can truthfully become source-implemented, a future change must bind one exact package digest to signed canonical metadata that includes at least the expected source/target build identity, update channel, package size/digest, rollback/recovery requirements and key identity. That metadata path must have explicit key lifecycle/revocation rules and fail closed on duplicate or ambiguous fields.

Before `recovery_handoff` can be implemented, the exact AOSP platform/recovery path must be built and exercised in the pinned SwirPhoneOS runtime, then tested with rollback evidence. No physical-device write path may be enabled from this preflight alone.

## Runtime evidence still required

The first real Cuttlefish build should verify that the document picker works, large-file hashing remains responsive, content-provider size behavior is handled correctly, state survives expected activity lifecycle changes, all localized strings fit, Arabic mirrors correctly and accessibility focus/labels are usable. Physical OTA/recovery validation remains a later exact-device gate.
