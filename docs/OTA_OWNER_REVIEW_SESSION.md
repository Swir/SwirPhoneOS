# Swir Update owner-selected OTA review session

Swir Update now has a source-stage, owner-driven review path that binds one local OTA ZIP to one canonical signed manifest and one detached RSA signature without staging or installing anything.

## Review sequence

1. The owner selects a local `.zip` through Android Storage Access Framework.
2. The package preflight streams the selected bytes, enforces the existing 16 GiB ceiling, validates the simple file name and ZIP header, and records the exact SHA-256 and byte count.
3. Only after that package is review-ready can the owner select a canonical `SWIR-OTA-MANIFEST-V1` document. The manifest is read into memory with the existing 4096-byte limit and must parse strictly.
4. Only after a valid manifest can the owner select its detached signature. Signature input is bounded to 1024 bytes.
5. `OtaReviewSession` asks the immutable `OtaTrustStore` to resolve the manifest key and then runs the existing exact signature/build/channel/package/rollback policy.

Selecting a different package clears the previously selected manifest and signature. Selecting a different manifest clears the previous signature. The app does not persist selected URI permissions or copy signed metadata into a staging directory.

## Current production result

`DefaultOtaTrustStore` intentionally contains zero production verification keys. Therefore the owner can exercise package and canonical-metadata preflight in source, but an authentic production review currently stops at the trust gate with an unknown key. No test key is silently promoted to production trust.

After a future reviewed public release key is provisioned, a completely valid session can reach only:

`AUTHENTIC_REVIEW_READY_NOT_STAGED`

That state means the detached signature and the exact package/build/channel/rollback binding were accepted for review. It is not installation authorization.

## Safety boundary

The review session is deliberately in-memory and read-only. It does not:

- stage or install an update package;
- invoke Android `RecoverySystem`, update-engine installation APIs or a reboot;
- write partitions, block devices or boot images;
- run shell commands, ADB or Fastboot;
- persist owner-selected metadata URI access;
- enable SwirRoot or authorize a privileged transition;
- satisfy Android runtime, physical-device, update/recovery or beta gates by itself.

`stagingAllowed()` remains hard-false in both the manifest policy and the owner review session.

## Verification

`OtaReviewSessionHostTest` generates an ephemeral RSA key pair and covers the successful review-only state, tampered signatures, stale-metadata invalidation after package replacement, bounded manifest/signature input, the empty production trust store and hard-false staging authorization.

`tests/test_android_apps_update_review_session.py` enforces the permission-free Storage Access Framework boundary, absence of write/install/process primitives, exact AOSP staging inclusion and complete EN/PL/NB/DE/ES/FR/PT/AR resource parity.

This remains `ANDROID_SOURCE` work. A real AOSP build, Cuttlefish execution, provisioned production public key, tested rollback/recovery path and physically validated supported device are still required before Swir Update can contribute to the `security_ota` milestone or any beta gate.
