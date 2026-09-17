# Device support readiness evidence

SwirPhoneOS does not treat a matching model/codename, a generic ARM64 GSI, or a successful read-only ADB/Fastboot inspection as proof that a phone is supported. Device support must be earned by exact-device evidence and must remain separate from preparation-only metadata.

`swirphoneos.device_support_readiness` is the schema-v1 bridge between the evidence we can safely collect today and the physical validation that still has to happen later. It performs no device I/O and cannot authorize flashing, root, unlock, reboot, erase, install, rollback or profile promotion.

## Inputs

A schema-v1 readiness report binds three already validated inputs:

1. one exact metadata-only `device_packs/<vendor>/<codename>/profile.json`, including the SHA-256 of the exact profile bytes;
2. one schema-v2 cross-transport read-only hardware evidence report produced from matching ADB and Fastboot observations;
3. one create-only recovery journal whose local install and rollback artifacts have already passed exact size/SHA-256 verification.

The collector rejects mismatched profile ids, codenames, model allowlists and current-build fingerprints. The hardware report and recovery journal are also bound by their own evidence SHA-256 values.

## What schema v1 can prove

Only preparation facts may be true:

- the metadata profile parsed under the fail-closed schema;
- the ADB/Fastboot observations were correlated by the existing read-only evidence validator;
- rollback artifacts were pre-verified locally in the recovery journal;
- the exact current firmware and intended target build were recorded together.

This is useful because it prevents later tooling from accidentally combining a profile from one device, a hardware observation from another device and rollback material prepared for a different firmware.

## What schema v1 deliberately cannot prove

The following support gates always remain false in schema v1:

- physical hardware verification;
- verified partition map;
- tested stock restore;
- SwirPhoneOS boot on the physical phone;
- physical install cycle;
- physical rollback cycle;
- usable core phone experience.

Device capabilities are separately reported as `UNVERIFIED` for telephony, camera, audio, Wi-Fi, Bluetooth, sensors, GNSS and NFC. A future device may be supportable with an explicitly documented limitation, but schema v1 never invents that result from host metadata.

Consequently every schema-v1 report is forced to keep:

- `support_status = NOT_SUPPORTED`;
- `support_claim_allowed = false`;
- `profile_promotion_allowed = false`;
- `install_allowed = false`;
- `device_write_allowed = false`;
- `root_allowed = false`;
- `status_promotion_performed = false`.

Even recomputing the report integrity hash after changing one of those fields does not make the report valid; the validator checks the semantic invariants independently of the digest.

## Read-only CLI

```bash
python -m swirphoneos.device_support_readiness_cli \
  --profile device_packs/oneplus/avicii/profile.json \
  --journal /absolute/path/to/recovery-journal.json \
  --hardware /absolute/path/to/hardware-evidence.json
```

The command prints JSON only after all three inputs validate and bind to one profile/current-build/target-build chain. It does not connect to a phone.

## Metadata profile hardening

Schema-v1 device profiles are explicitly non-operational. The loader now rejects:

- symlinked `profile.json` files and symlinked registry roots;
- duplicate JSON keys at any nesting level;
- empty or oversized files;
- a `VERIFIED` status;
- any non-null `verified_partition_map`;
- any claimed `validated_builds` or `recovery_evidence`;
- executable flash operations or `flash_enabled=true`;
- duplicate sources/models;
- a profile id that does not match the `vendor/codename/profile.json` registry path during discovery.

`load_profile_snapshot()` returns a SHA-256 over the exact bytes that were validated so evidence can bind to the reviewed profile, not only to its human-readable id.

## Promotion rule

A support-capable profile/evidence schema must be introduced explicitly rather than loosening schema v1 in place. Before a physical profile can become supported, SwirPhoneOS still needs reviewed evidence for at least:

1. one owner-controlled physical device matching the intended model/codename and exact firmware baseline;
2. an exact reviewed partition/layout map for that build;
3. a tested stock restore path;
4. a SwirPhoneOS image built from reproducible source and booted on that phone;
5. an owner-confirmed install cycle and a successful rollback/recovery cycle;
6. usable core-device runtime checks, with telephony/camera and other hardware capabilities truthfully recorded per device;
7. a separate exact-build SwirRoot cycle only if that device/build is later allowlisted for root.

Until those artifacts exist, `oneplus/avicii` remains `PLANNED_NOT_SUPPORTED`, the installer remains disabled for that profile, and the project must not advertise the phone as supported.
