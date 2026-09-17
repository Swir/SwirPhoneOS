# Physical Device Validation Evidence

SwirPhoneOS does not treat a model name, Treble/GSI eligibility, an unlocked bootloader, or read-only ADB/Fastboot correlation as proof that a phone is supported. Support must be earned with exact-device, exact-build physical evidence.

`swirphoneos.device_physical_validation` implements a host-only schema-v2 evidence binder after the existing preparation-only `device_support_readiness` projection. It reads local JSON/evidence files and validates identity, build continuity, file size and SHA-256 provenance. It does **not** execute `adb`, `fastboot`, flash, erase, reboot, install, root, unroot, unlock a bootloader, change slots, modify a profile, or authorize a device write.

## Required physical gates

A validation record covers every physical gate that schema-v1 readiness deliberately leaves false:

- physical hardware verification;
- verified partition map;
- stock restore;
- SwirPhoneOS boot on the target phone;
- install cycle;
- rollback cycle;
- core phone experience.

Each gate is `PASS` or `FAIL` and must bind a distinct local evidence file by portable relative path, exact byte size and SHA-256. The evidence root must be an absolute existing non-symlink directory. Traversal, symlink components, missing files, duplicate paths, size drift and digest drift fail closed.

## Capability review

The same session records telephony, camera, audio, Wi-Fi, Bluetooth, sensors, GNSS and NFC. A capability is `PASS`, `FAIL`, `NOT_APPLICABLE` or `NOT_TESTED`.

`PASS`, `FAIL` and `NOT_APPLICABLE` require bound evidence. `NOT_TESTED` deliberately carries no evidence and prevents support-candidate review. Audio, Wi-Fi and sensors are treated as core device basics and must pass before candidate review becomes ready. Other capabilities may remain a truthfully documented known failure at this review layer; beta/release policy decides separately whether a tested limitation is acceptable for a particular release.

## Strong binding model

Schema v2 keeps evidence metadata directly under the exact physical test or capability name instead of publishing an unbound flat file inventory. The generated report therefore preserves the relationship between:

- test/capability identity;
- result state;
- evidence path;
- evidence byte size;
- evidence SHA-256;
- evidence kind;
- observation time;
- review notes;
- successful local evidence verification.

The report also binds the exact readiness report, profile SHA-256, current firmware/build, target SwirPhoneOS build, hardware-evidence hash and recovery-journal hash. Reusing one evidence file for multiple gates/capabilities is rejected.

The canonical report has an integrity SHA-256, but this is tamper detection, not a digital signature. Preserve the original local evidence files and readiness input for audit.

## Non-authorizing result

Even a complete, internally consistent bundle with `support_candidate_review_ready=true` must retain:

- `support_status=NOT_SUPPORTED`;
- `support_claim_allowed=false`;
- `profile_promotion_allowed=false`;
- `install_allowed=false`;
- `device_write_allowed=false`;
- `root_allowed=false`;
- `status_promotion_performed=false`.

This is intentional. Candidate readiness is an input to human/code review, not an automatic switch that makes a phone supported. Checked-in device-profile status remains authoritative until a separate reviewed promotion policy is implemented.

## Operator record

The record uses `schema_version=2` and `source=owner_physical_validation_record`. It must bind the exact profile ID, model, codename, current firmware fingerprint, target build and `evidence_sha256` from the support-readiness report. It also records whether the owner was present and whether physical write activity performed outside this review-only tool was recorded. A successful install/rollback session cannot be represented as all-green while pretending no external write activity occurred.

## Run the binder

```bash
python -m swirphoneos.device_physical_validation_cli \
  --readiness /absolute/path/device-support-readiness.json \
  --record /absolute/path/physical-validation-record.json \
  --evidence-root /absolute/path/evidence
```

The result is JSON on stdout. A malformed schema, identity/build mismatch, readiness-integrity failure, unsafe path, file mutation or semantic overclaim returns a failure instead of a partial success report.

## OnePlus Nord / avicii status

The checked-in `oneplus/avicii` profile remains `PLANNED_NOT_SUPPORTED`. No real physical validation bundle has been captured in this repository. There is still no verified partition map, stock-restore proof, physical SwirPhoneOS boot, install/rollback cycle or exact-device capability matrix.

The legitimate hardware sequence remains owner-controlled and evidence-first: read-only identity correlation, recovery/restore preparation, separately reviewed physical tests, then packaging those real outcomes with this binder. This module itself never performs the hardware operation.
