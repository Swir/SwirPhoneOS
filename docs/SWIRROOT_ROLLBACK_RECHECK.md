# SwirRoot rollback-material recheck

SwirRoot must never rely on a stale recovery journal as proof that rollback material is still usable. A journal records that local files matched their declared size and SHA-256 when the journal was created; those files can later be deleted, replaced, truncated or redirected. The rollback-material recheck closes that time-of-check/time-of-use gap before a SwirRoot readiness review.

## Scope

`swirphoneos.rollback_material_evidence` is a host-side, read-only evidence collector. It receives a validated recovery journal plus one absolute trusted artifact directory. It reopens every journal entry whose kind is `rollback`, verifies that every path remains confined below the trusted root, rejects symlinks, checks the exact byte size and recomputes SHA-256.

The resulting schema-v1 evidence binds the current rollback bytes to the journal's transaction id, device profile, model/codename, current firmware, target SwirPhoneOS build and journal evidence digest. The report intentionally does not include the absolute local artifact-root path.

The collector has no ADB, Fastboot, process-execution, network, root, unlock, reboot, flash, erase or partition-write capability. Its authorization fields are permanently false.

## SwirRoot readiness integration

SwirRoot readiness schema v2 no longer treats `journal.rollback_ready=true` by itself as a passed `rollback_material_verified` gate. The gate is true only when fresh rollback-material evidence validates and matches the exact journal used by the readiness report.

If fresh material is omitted, readiness remains valid as a diagnostic projection but reports:

- `evidence_bindings.rollback_material_rechecked=false`
- `policy_gates.rollback_material_verified=false`
- `rollback_material_verified` in `missing_requirements` for enable/unroot actions

The CLI requires the fresh recheck path:

```bash
python -m swirphoneos.root_readiness_cli \
  --action enable \
  --exact-build '<exact SwirPhoneOS build fingerprint>' \
  --journal /absolute/path/recovery-journal.json \
  --hardware /absolute/path/hardware-evidence.json \
  --artifact-root /absolute/path/to/reviewed-artifacts
```

A standalone recheck can also be produced without generating SwirRoot readiness:

```bash
python -m swirphoneos.rollback_material_cli \
  --journal /absolute/path/recovery-journal.json \
  --artifact-root /absolute/path/to/reviewed-artifacts
```

Neither command changes a phone.

## What this does not prove

A successful recheck proves only that the exact local rollback files still match the journal at collection time. It does **not** prove that the device is supported, that its partition map is verified, that the rollback image is correct for unseen hardware, that a physical restore has succeeded, that the bootloader may be bypassed, or that a root transition is authorized.

SwirRoot remains unavailable until all independent policy gates are satisfied, an exact build is explicitly allowlisted, a legitimate mutation backend exists, physical install/restore evidence exists, and owner confirmation is collected at the actual transition boundary.

## Safety invariants

The implementation fails closed on missing or changed files, size/hash drift, traversal, symlinks, duplicate JSON keys, malformed evidence, journal/evidence identity drift and forged authorization fields. Recomputing the report integrity hash after changing `device_write_allowed`, `root_operation_executed` or `status_promotion_performed` does not make the report valid.

This evidence is preparation infrastructure only. It does not change the weighted project progress or the beta-release gates.
