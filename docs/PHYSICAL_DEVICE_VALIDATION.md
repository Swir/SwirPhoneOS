# Physical Device Validation Evidence

SwirPhoneOS does not treat a model name, a Treble/GSI label, an unlocked bootloader, or a successful read-only ADB/Fastboot observation as proof that a phone is supported. Physical support must be earned with exact-device, exact-build evidence.

This document defines the schema-v1 physical validation review bundle implemented by `swirphoneos.device_physical_validation`. The tooling is intentionally **host-only and non-authorizing**: it reads local JSON/evidence files, validates hashes and identity/build continuity, and produces a tamper-evident review report. It does not execute `adb`, `fastboot`, flash, reboot, erase, install, root, unroot, change slots, unlock a bootloader, or modify a device profile.

## Why this layer exists

`device_support_readiness` deliberately stops before physical validation. It can prove that a metadata-only device profile, cross-transport read-only hardware observation and pre-write recovery journal all refer to the same profile/current-build/target-build tuple. Its physical gates remain false by design.

The physical validation layer consumes that immutable readiness report and binds it to evidence for every physical gate that was previously missing:

- physical hardware verification,
- verified partition map,
- stock restore,
- SwirPhoneOS boot on the target phone,
- install cycle,
- rollback cycle,
- core phone experience.

Every gate must have a distinct evidence file with an exact byte size and SHA-256 digest. Evidence paths are relative to one explicitly selected local evidence root. Traversal, symlinks, duplicate paths, missing files, size drift and digest drift fail closed.

## Capability review

The same validation session records all currently tracked device capabilities:

- telephony,
- camera,
- audio,
- Wi-Fi,
- Bluetooth,
- sensors,
- GNSS,
- NFC.

A capability state is one of `PASS`, `FAIL`, `NOT_APPLICABLE` or `NOT_TESTED`. `PASS`, `FAIL` and `NOT_APPLICABLE` require a bound evidence file. `NOT_TESTED` carries no evidence and prevents the bundle from becoming ready for support-candidate review.

For candidate review, audio, Wi-Fi and sensors must pass because they are treated as core device basics. Other capabilities may be recorded as known failures or not applicable, but they must be reviewed truthfully. This distinction is deliberate: a physically reviewed device can still have known issues, while a beta/release decision applies a separate policy about which issues are acceptable.

## Non-authorizing result

Even when every physical gate passes and the report says `support_candidate_review_ready=true`, schema v1 still requires:

- `support_status=NOT_SUPPORTED`,
- `support_claim_allowed=false`,
- `profile_promotion_allowed=false`,
- `install_allowed=false`,
- `device_write_allowed=false`,
- `root_allowed=false`,
- `status_promotion_performed=false`.

This is intentional. A complete validation bundle is input to code review and future profile-promotion policy; it is not a hidden automatic support switch. The checked-in device profile remains the authoritative public support status.

## Operator record

The owner/operator record is strict JSON with `source=owner_physical_validation_record`. It binds the exact profile, device model/codename, current firmware fingerprint, target SwirPhoneOS build and the `evidence_sha256` of the preparation readiness report.

Each physical test entry records:

- the required test ID,
- `PASS` or `FAIL`,
- evidence file path/size/SHA-256,
- evidence type (`AUTOMATED_CAPTURE`, `MANUAL_OBSERVATION` or `HYBRID`),
- UTC observation time,
- review notes.

The record also states whether the owner was present and whether physical write activity performed outside this review-only tool was recorded. The latter is required for an internally consistent all-green install/rollback session; it does **not** mean this tool authorized the write.

## Run the binder

```bash
python -m swirphoneos.device_physical_validation_cli \
  --readiness /absolute/path/device-support-readiness.json \
  --record /absolute/path/physical-validation-record.json \
  --evidence-root /absolute/path/evidence
```

The JSON output should be preserved together with the referenced evidence files and the exact readiness input. Do not edit and re-hash a failed report to force it green: semantic validation recomputes candidate state from the physical test/capability inventory and keeps all support/write/root/promotion flags denied.

## OnePlus Nord / avicii status

The checked-in `oneplus/avicii` profile remains `PLANNED_NOT_SUPPORTED`. No physical validation bundle has been captured in this repository. There is no verified partition map, stock-restore proof, physical SwirPhoneOS boot, install/rollback cycle, or exact-device capability matrix yet.

The next legitimate hardware step is owner-controlled read-only identity evidence first, followed by separately reviewed recovery/install test preparation. Only after real physical testing exists should this binder be used to package the evidence for review.
