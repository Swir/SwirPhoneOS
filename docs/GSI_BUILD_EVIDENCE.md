# ARM64 GSI build evidence

SwirPhoneOS includes a source-level ARM64 Generic System Image target for the pinned Android 17 baseline. This target exists to make broad Treble-oriented platform testing possible without pretending that one image is safe for every Android phone.

## Current status

The checked-in product is `swirphoneos_gsi_arm64-aosp_current-userdebug`. It inherits the standard AOSP ARM64 product plus the AOSP GSI release configuration and includes the same twenty first-party SwirPhoneOS application modules as the Cuttlefish developer product.

**No SwirPhoneOS ARM64 GSI has completed a real build yet.** The `gsi_validation` milestone remains incomplete. A checked-in makefile, a host-side plan, green unit tests, or even a successfully hashed `system.img` is not by itself proof of Treble/VTS compliance, physical boot compatibility, safe installation, rollback, telephony, cameras, encryption, suspend, charging or any other device-specific behavior.

## Source contract

Run:

```bash
python -m swirphoneos gsi-contract
```

The contract fails closed unless the product:

- is registered as `swirphoneos_gsi_arm64`, device `generic_arm64`, architecture `arm64`;
- exposes `swirphoneos_gsi_arm64-aosp_current-userdebug`;
- inherits the reviewed AOSP ARM64 and GSI release product definitions;
- preserves SwirPhoneOS product identity;
- includes all twenty current source-ready first-party apps;
- contains no reviewed security/signing weakening tokens; and
- is included exactly in the bounded `vendor/swir/` staging manifest.

The public contract always reports build, Treble/VTS, physical compatibility, installation and release status as unverified.

## Reproducible build plan

Generate the exact-tag plan without executing it:

```bash
python -m swirphoneos gsi-plan \
  --workspace /path/to/aosp \
  --jobs 16
```

The plan keeps the repository baseline at `android-17.0.0_r1`, captures a resolved `repo manifest -r`, stages only reviewed Swir source, selects the SwirPhoneOS ARM64 GSI lunch target and requests only `systemimage` from the Android build system. The expected image path is:

```text
out/target/product/generic_arm64/system.img
```

The plan performs no phone command and cannot authorize flashing.

## Dedicated builder workflow

`.github/workflows/gsi-build-evidence.yml` is manual-only and requires the dedicated self-hosted runner label `swir-aosp-builder`. It shares the same concurrency group as the Cuttlefish build so the persistent AOSP workspace cannot be modified by two SwirPhoneOS platform builds at once.

The workflow:

1. records the source commit and requested parallelism;
2. runs the existing full-build host preflight;
3. validates the checked-in GSI source contract and deterministic plan;
4. initializes/synchronizes exact `android-17.0.0_r1` source;
5. records `repo manifest -r` evidence;
6. stages the exact reviewed `vendor/swir/` tree and requires schema-v5 closure;
7. builds `systemimage` for `swirphoneos_gsi_arm64-aosp_current-userdebug`;
8. re-verifies the complete staged Swir tree after Kati/Soong/Ninja;
9. hashes and validates the produced `system.img`; and
10. uploads only bounded evidence files and, on failure, at most the final 256 KiB build-log tail.

The workflow does **not** use ADB/Fastboot, unlock, boot, flash, erase, change slots, modify a phone, or enable SwirRoot.

## Build evidence

After a successful local GSI build:

```bash
python -m swirphoneos gsi-build-evidence \
  --workspace /path/to/aosp \
  --manifest /path/to/aosp/swirphoneos-gsi-pinned-manifest.xml \
  --baseline platform/aosp_baseline.json
```

The collector requires:

- an initialized AOSP workspace;
- a fully SHA-pinned resolved Repo manifest;
- a non-empty regular `generic_arm64/system.img`;
- SwirPhoneOS ARM64 product fingerprint identity; and
- exact Android release, API, build ID, security patch and `userdebug` type matching the pinned baseline.

It records the image byte size and SHA-256 together with source-manifest and build identity. The report intentionally fixes these flags to false:

- `treble_vts_verified`
- `physical_device_compatibility_verified`
- `install_verified`
- `rollback_verified`
- `device_write_allowed`
- `status_promotion_performed`
- `release_artifact`

## Required validation before any device claim

A future GSI milestone requires more than a successful build. At minimum, the exact candidate must receive relevant Treble/VTS validation, a documented compatibility matrix, and controlled physical testing on explicitly identified owner-controlled devices. Each device still needs its own bootloader state, firmware/vendor interface, partition/recovery and rollback review.

The existing OnePlus Nord AC2003 (`avicii`) profile remains `PLANNED_NOT_SUPPORTED`. A generic ARM64 GSI result must never be converted automatically into an `avicii` support or flashing authorization.

## Release boundary

GSI build evidence may eventually satisfy part of the engineering evidence for the `gsi_validation` milestone, but it does not by itself satisfy that milestone and never bypasses the beta gates. A beta still requires a reproducible OS build and boot, safe install/rollback/recovery, at least one physically verified supported phone profile, usable core phone functionality and reviewed release artifacts/checksums.
