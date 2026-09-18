# SwirRoot readiness evidence

SwirRoot readiness evidence is a **read-only engineering projection**. Schema v2 binds the recovery journal, a fresh exact-byte rollback-material recheck, read-only ADB/Fastboot correlation and SwirRoot policy to one exact SwirPhoneOS build, then reports which policy gates are still missing.

It does **not** perform root, unroot, boot-image modification, bootloader unlock, flash, erase, reboot or any other device write. It does not turn the current `oneplus/avicii` profile into a supported device and it does not make the current SwirRoot source a working root implementation.

## Why this exists

Before an owner-facing enable/unroot workflow can be trusted, evidence from different subsystems must refer to the same device profile and build. A recovery journal proves that reviewed local target/rollback files matched their declared digests when the journal was created, but those files can later change. Read-only hardware correlation can show that ADB and Fastboot observations are internally consistent. Neither is sufficient to authorize root.

`swirphoneos.swirroot_readiness` combines those evidence classes without weakening either one. Schema v2 additionally requires a fresh rollback-file recheck before `rollback_material_verified` can pass. It rejects cross-profile, cross-model, cross-codename, current-firmware, target-build, journal or rollback-inventory mismatches and produces a canonical SHA-256 over the final projection.

## Evidence bindings

A report keeps these preparation bindings explicit:

- recovery journal `profile_id` equals hardware evidence `profile_id`;
- journal device model matches the ADB-reported model;
- journal codename matches the ADB-reported codename;
- the ADB-observed firmware fingerprint equals the journal's `expected_current_build`;
- the requested exact SwirPhoneOS build equals the journal's `target_build`;
- both source reports pass their own integrity/schema validation;
- `rollback_material_rechecked=true` only when every rollback file has just been re-read and still matches the journal's exact size and SHA-256.

The readiness report stores the SHA-256 identifiers of its journal and hardware evidence. The rollback recheck itself is bound to the journal digest and the same transaction/profile/model/codename/current-build/target-build tuple; see `SWIRROOT_ROLLBACK_RECHECK.md`.

If the fresh rollback recheck is omitted, the report remains a useful diagnostic projection but `rollback_material_verified=false` and that requirement remains missing.

## Policy-gate projection

Both `enable` and `unroot` now require the same complete recovery-safe gate set:

- `exact_build_match`;
- `verified_device_profile`;
- `owner_confirmation`;
- `rollback_material_verified`;
- `journal_available`;
- `update_state_safe`;
- `expected_nonroot_state_known`.

The symmetry is intentional. Enabling root is blocked until the expected non-root restore state is already known, so a future backend cannot enter a rooted state without a defined unroot target. Unroot is also blocked unless the device profile is verified and the update state is safe, preventing a future write-capable path from weakening identity or OTA-safety requirements during restoration.

A journal by itself no longer satisfies `rollback_material_verified`. That gate passes only after the exact rollback bytes are rechecked against the bound journal during readiness collection. The current cross-transport hardware evidence is intentionally only `CORRELATED_READ_ONLY_NOT_VERIFIED`, so it cannot establish a verified device profile or root authorization. The journal also deliberately records `owner_confirmation_recorded=false`. No current evidence object proves update-state safety or the authoritative expected non-root runtime state.

Therefore a valid report can still—and currently must—be **blocked**. This distinguishes "the preparation evidence agrees" from "root is safe to execute".

## CLI

After creating a recovery journal and read-only hardware evidence for the same reviewed device/build tuple, keep the exact reviewed rollback files under one trusted absolute artifact directory and run:

```sh
python -m swirphoneos.root_readiness_cli \
  --action enable \
  --exact-build '<exact SwirPhoneOS fingerprint/build identity>' \
  --journal /absolute/path/to/recovery-journal.json \
  --hardware /absolute/path/to/hardware-evidence.json \
  --artifact-root /absolute/path/to/reviewed-artifacts
```

For unroot planning use `--action unroot` with the same exact-build binding. `--artifact-root` is mandatory in the CLI so the normal operator path cannot silently rely on stale journal metadata.

The command prints JSON only after all input evidence, current rollback bytes and bindings validate. The output always keeps:

```text
device_write_allowed=false
root_operation_executed=false
status_promotion_performed=false
```

A report also exposes `missing_requirements`, `policy_backend_available`, `hardware_root_authorized` and `transition_ready`. With the repository's current policy (`write_operations_enabled=false`, zero supported builds) and current correlation-only hardware evidence, `transition_ready` is false.

## What still blocks executable SwirRoot

A future executable backend needs independent evidence that does not exist today:

1. a reproducible SwirPhoneOS build and real boot;
2. an exact physically verified supported device profile/build;
3. a tested install/recovery/stock-restore path;
4. durable owner confirmation bound to the exact transition;
5. authoritative safe-update-state evidence;
6. a known and verified non-root boot/system state before enable and during unroot;
7. an exact-build mutation backend using legitimate owner-supported boot/image paths;
8. physical enable → reboot → use → unroot → reboot/recovery validation.

Only after those requirements exist should the policy's supported-build/write switches be reviewed. They must never be enabled merely to make readiness tooling report green.
