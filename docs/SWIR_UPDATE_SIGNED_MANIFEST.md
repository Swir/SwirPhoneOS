# Swir Update signed manifest trust binding

Swir Update now has a dependency-free source-stage policy for authenticating canonical OTA metadata and binding that metadata to the exact bytes already inspected by the local package preflight. This is a review gate only. It does not stage, install, flash, reboot or hand a package to recovery.

## Canonical format

The detached signature covers the exact UTF-8 bytes of a fixed-order manifest. The parser accepts exactly nine lines, rejects CR/NUL, rejects unknown or reordered fields, limits the complete metadata to 4096 bytes, and does not normalize a permissive JSON representation.

```text
SWIR-OTA-MANIFEST-V1
source_fingerprint=<exact current build fingerprint>
target_fingerprint=<exact intended target build fingerprint>
channel=<STABLE|BETA|DEVELOPER>
package_name=<simple .zip file name>
package_size=<positive decimal byte count>
package_sha256=<64 lowercase hex characters>
key_id=<reviewed key identifier>
rollback_required=<true|false>
```

`package_size` must be greater than zero and no larger than the same 16 GiB ceiling used by the local package preflight. `package_name` uses the same simple-name policy as the selected archive. The SHA-256 value is canonical lowercase hexadecimal.

## Review chain

`UpdatePolicy.reviewSignedManifest(...)` requires all of the following before returning `AUTHENTIC_REVIEW_READY_NOT_STAGED`:

1. the manifest parses under the exact canonical grammar;
2. the detached `SHA256withRSA` signature verifies with the supplied trusted public key;
3. `key_id` exactly matches the reviewed trusted-key identifier supplied by the caller;
4. `source_fingerprint` exactly matches the currently running build identity supplied by the caller;
5. the target fingerprint is non-empty and syntactically bounded;
6. the signed channel exactly matches the expected current update channel;
7. the signed package name, byte size and SHA-256 exactly match the owner-selected `PackageInspection` result;
8. `rollback_required=true`.

Any mismatch fails closed into a specific rejected review state. Package identity is therefore no longer separable from signed source/target/channel/key/rollback metadata at the policy layer.

## Deliberate safety boundary

Even a successful signed review returns `stagingAllowed() == false`. The implementation contains no `RecoverySystem`, `DownloadManager`, process execution, block-device path, reboot, flash or partition-write path. It does not advance `staged_update_state`, `recovery_handoff`, the `security_ota` milestone or any beta gate.

The current Android UI still exposes only the owner-selected local ZIP byte-identity preflight. A later reviewed integration must add an owner-visible way to select/obtain the exact manifest and detached signature and must bind them to a production trust store/key-lifecycle policy before this source-stage verifier is used as a real update authenticity surface.

## Key lifecycle still required

Passing a public key and matching key identifier to the policy is not a complete release-signing system. Before staging is enabled, SwirPhoneOS still needs a reviewed trust-store design covering at least:

- offline release-key custody and release signing procedure;
- explicit active/revoked/retired key identifiers;
- signed key rotation or another fail-closed transition mechanism;
- candidate/version rollback policy and anti-downgrade rules appropriate to the platform;
- exact target product/device/build compatibility rules;
- recovery/update-engine integration and tested rollback evidence.

## Verification

The dependency-free Java host test creates a real RSA key pair, signs canonical metadata and verifies the successful exact binding. Negative cases cover metadata tampering, wrong key ID, wrong source build, wrong channel, mismatched selected package, missing rollback requirement, unknown extra fields and non-canonical digest encoding. Python source-policy coverage additionally locks the canonical field inventory and the invariant that signed review never authorizes staging.

Runtime evidence remains mandatory before any stronger claim. A real built SwirPhoneOS image must exercise the full signed-manifest UI/trust-store/update path, followed later by exact-device install, rollback and recovery validation.
