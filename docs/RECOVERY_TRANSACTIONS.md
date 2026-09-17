# Recovery transaction evidence

SwirPhoneOS does not currently expose a write-capable installer. This document defines the **local preparation and evidence layer** that must exist before a future device-specific install/rollback implementation can be considered.

The implementation is `swirphoneos.transaction_evidence` plus `swirphoneos.journal_evidence`. They perform only local metadata validation, file hashing, create-only JSON journaling and journal-integrity revalidation. They do **not** invoke ADB, Fastboot, a bootloader, recovery, an updater, SwirRoot, a shell, or any external-device command.

## Why this exists

A safe install path needs more than a target image. Before a device mutation is even eligible for review, SwirPhoneOS must be able to prove that the intended target and the matching rollback material are the exact files the owner reviewed, that the plan is bound to one profile/current-build/target-build combination, and that the evidence survives a desktop crash as a durable local journal.

Schema v1 deliberately cannot authorize writes. Every accepted plan requires:

- `write_enabled: false`;
- `owner_confirmation_required: true`;
- `rollback_required: true`;
- one exact device profile id, codename and model;
- an expected current build identity and target build identity;
- at least one install artifact and at least one rollback artifact;
- exact byte size and SHA-256 for every artifact;
- globally unique, relative POSIX artifact paths with no traversal.

Unknown fields, duplicate JSON keys, absolute/traversal paths, symlinked artifacts, size drift and SHA-256 drift are rejected fail-closed.

## CLI

Validate a plan without touching artifact bytes:

```sh
python -m swirphoneos transaction-plan --file /absolute/path/to/plan.json
```

Verify all local artifact bytes against the reviewed plan:

```sh
python -m swirphoneos transaction-evidence \
  --plan /absolute/path/to/plan.json \
  --artifacts /absolute/path/to/artifact-root
```

Optionally persist the verified result as a new local journal:

```sh
python -m swirphoneos transaction-evidence \
  --plan /absolute/path/to/plan.json \
  --artifacts /absolute/path/to/artifact-root \
  --journal /absolute/path/to/recovery-journal.json
```

Revalidate a persisted journal later, including its canonical evidence hash and immutable safety fields:

```sh
python -m swirphoneos transaction-journal \
  --file /absolute/path/to/recovery-journal.json
```

The journal path must not already exist. The writer uses exclusive creation, requests owner-only permissions on POSIX, flushes and fsyncs the file, and never overwrites a prior journal. The journal records the canonical plan SHA-256, exact artifact hashes, source/target build identities, `rollback_ready: true`, `owner_confirmation_recorded: false`, and `write_allowed: false`. Revalidation rejects duplicate keys, changed build/artifact fields, changed safety booleans and any canonical evidence-hash mismatch.

## SwirRoot integration boundary

`journal_evidence.swirroot_gate_projection()` maps only what a validated local journal can truthfully prove into the SwirRoot gate vocabulary. It can prove that rollback material was reviewed and that a matching journal exists; it can also compare the journal's target build/profile to a requested exact build/profile. It deliberately keeps `verified_device_profile`, `owner_confirmation`, `update_state_safe`, `expected_nonroot_state_known` and `transition_allowed` false because those facts require independent physical/runtime evidence. Therefore a transaction journal can satisfy prerequisites without ever enabling SwirRoot by itself.

## Non-goals in schema v1

Schema v1 does not contain commands, partition names, slot-switch instructions, unlock operations or executable steps. It cannot mark hardware verified, cannot grant SwirRoot, cannot install an update and cannot transition a profile to supported. A future write-capable layer must be a separate reviewed component and must consume stronger physical evidence rather than weakening this schema.

For the current `oneplus/avicii` device pack, the profile remains `PLANNED_NOT_SUPPORTED`. No partition map, firmware baseline, validated SwirPhoneOS build or recovery evidence has been established on physical hardware.

## Future gate before writes

A later device-specific transaction engine must, at minimum, bind this journal to all of the following before it can offer an owner-visible write action:

1. an exact hardware-verified device profile and firmware/build identity;
2. a reviewed partition/slot map for that exact profile;
3. complete rollback material verified by this evidence layer;
4. an explicit owner confirmation captured **after** diagnostics and recovery review;
5. durable in-progress state with deterministic crash/restart recovery;
6. a tested stock-restore path on the same model/firmware;
7. update/recovery/SwirRoot coordination so no component mutates the same boot state concurrently;
8. physical install → boot → rollback/restore evidence.

Until those requirements are met, the project must continue to report `write_allowed: false`, `install_restore` incomplete and Beta blocked.
