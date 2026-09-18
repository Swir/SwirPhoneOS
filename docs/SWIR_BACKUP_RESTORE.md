# Swir Backup verified document backup and restore

Status: **source-stage implementation; Android runtime not yet verified**.

Swir Backup is the first-party document backup surface for SwirPhoneOS. This implementation intentionally operates only on documents that the owner selects through Android's Storage Access Framework (SAF). It does not read another application's private storage, device partitions, recovery partitions, credentials, or hidden system state, and it does not require broad external-storage permissions.

## Schema v2 archive integrity

New `.swirbackup` archives use manifest schema 2. The manifest must be the first ZIP entry and is bounded to 64 KiB. It records the exact SwirPhoneOS build fingerprint, Android SDK level and, for every selected document, the deterministic archive entry name, sanitized display name, byte length and lowercase SHA-256 digest. Parsing is fail-closed: duplicate or unknown keys, non-canonical numbers/Base64 fields, invalid hashes, unsafe names, count drift, unexpected entry order, extra entries and size-limit violations are rejected.

The current bounds are 64 documents, 128 MiB per document and 512 MiB total document payload. These are safety/resource limits rather than promises about provider capacity.

During backup creation each selected source is read once to compute its expected byte length and SHA-256, then read again while it is copied into the ZIP. The second read must exactly match the first. If a provider changes the selected document between those reads, creation fails instead of silently producing a manifest that describes different bytes.

Schema 1 archives created by the earlier source stage remain eligible for bounded structural inspection only. They do not contain per-document integrity metadata, so this implementation deliberately refuses to restore them.

## Owner-selected restore

Restore is explicit and two-step:

1. The owner chooses a `.swirbackup` archive with `ACTION_OPEN_DOCUMENT`.
2. The owner chooses the destination folder with `ACTION_OPEN_DOCUMENT_TREE`.

Before any destination write, the entire schema-v2 archive is verified without extracting files. The archive is then reopened and its canonical manifest is checked again before restore staging begins. Documents are created only under the selected SAF tree with temporary names, hashed while they are written, and accepted only when their byte length and SHA-256 match the manifest. After all entries pass, the temporary documents are renamed to sanitized user-facing names.

If a restore step fails, Swir Backup attempts to delete all documents it created during that operation. Cleanup is best-effort because behavior is ultimately controlled by the selected `DocumentsProvider`; a provider can fail or refuse delete/rename operations. Swir Backup never overwrites a raw filesystem path and never treats provider-specific rename behavior as a hardware/recovery rollback guarantee.

## Security boundaries

SHA-256 in schema 2 provides byte-integrity detection inside the archive; it is **not** a digital signature or proof that an archive came from a trusted SwirPhoneOS installation. Future authenticated/exported backup formats would need a separate signing/key-management design.

This document restore path is distinct from SwirPhoneOS partition/recovery rollback. It cannot satisfy the `install_restore` milestone, the physical-device rollback gate, SwirRoot rollback requirements, or beta readiness. Those remain bound to exact device/profile/build evidence and real-device recovery testing.

## Localization and UI

All user-visible backup/restore messages are Android resources with complete EN/PL/NB/DE/ES/FR/PT/AR catalogs. The activity consumes shared `SwirDesign` background, text, spacing and minimum 48 dp touch-target tokens. Source contracts do not prove rendered quality, RTL mirroring, accessibility, provider compatibility or successful restore on a built image; those require the pending AOSP/Cuttlefish runtime review and later physical-device validation.

## Required runtime validation

Before this feature can be described as runtime-verified, a built SwirPhoneOS image must exercise at least: schema-v2 create → inspect → restore, a deliberate digest mismatch, an oversized entry, an archive with an unexpected extra entry, legacy schema-v1 inspect-only behavior, user cancellation at both pickers, a provider that cannot rename/delete, duplicate destination-name behavior, EN/PL/NB/DE/ES/FR/PT/AR UI launch, Arabic RTL, accessibility focus/touch targets and process restart during or between operations.
