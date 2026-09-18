# Swir Update OTA trust store

Swir Update uses an immutable, fail-closed public-key registry for signed OTA manifest review. This layer exists to prevent an arbitrary caller-supplied verification key from becoming a de facto update trust anchor.

## Current status

This is **source-stage trust infrastructure only**. The default production registry intentionally contains **zero provisioned keys**. No release signing key is claimed, no package is staged, no recovery handoff is enabled, no reboot is requested, and no block-device write is authorized.

A real SwirPhoneOS release key may be added only as a deliberate reviewed source change after release engineering defines the key-generation, offline private-key custody, rotation, revocation and incident-response process. Private signing material must never be committed to this repository or shipped in the OS image.

## Trust entry contract

Each registry entry binds all of the following:

- a canonical lowercase `key_id` containing only `a-z`, `0-9`, `.`, `_` and `-`;
- an RSA public verification key;
- the exact lowercase SHA-256 digest of the key's SubjectPublicKeyInfo bytes;
- lifecycle state: `ACTIVE`, `RETIRED` or `REVOKED`;
- an explicit allowed update-channel set; `UNKNOWN` is never allowed.

The store rejects null entries, duplicate key IDs, more than 32 entries, non-RSA keys, malformed identifiers, malformed or mismatching SPKI digests, empty channel sets and any allowlist containing `UNKNOWN`.

Entries are sorted by key ID before the store's deterministic canonical digest is computed. The digest is evidence for the exact public trust configuration, not an installation authorization token.

## Resolution rules

A manifest key is usable only when all of these checks succeed:

1. the manifest is the strict canonical `SWIR-OTA-MANIFEST-V1` format;
2. `key_id` resolves to an entry in the immutable registry;
3. the public key still hashes to the pinned SPKI SHA-256 value;
4. the key lifecycle state is `ACTIVE`;
5. the manifest channel is explicitly allowed by that key;
6. the detached RSA signature validates with the resolved public key;
7. the existing Swir Update policy validates source fingerprint, target fingerprint, channel, exact owner-selected package name, exact package size, exact package SHA-256 and mandatory rollback policy.

Unknown, retired, revoked, wrong-channel or identity-mismatched keys fail closed before an OTA can be considered authentic-review-ready.

## Release-key lifecycle

The intended lifecycle is:

- **ACTIVE** — may validate only the explicitly allowlisted channels.
- **RETIRED** — retained for evidence/history but cannot authorize new OTA review.
- **REVOKED** — explicitly distrusted and cannot authorize OTA review.

Rotation must add the successor public key as a separately reviewable entry, move the predecessor out of `ACTIVE` according to release policy, and regenerate/verify trust-store evidence. Rotation must never reuse a key ID for different key bytes.

Emergency revocation must be an explicit source and release action backed by a new trusted OS/update path; merely editing metadata signed by the compromised key is not a revocation mechanism.

## Default production behavior

`DefaultOtaTrustStore.create()` currently returns an empty store. This is intentional. Host tests generate ephemeral RSA key pairs at test time; those keys are never part of the production trust root.

Until a reviewed production public key is provisioned, signed-manifest review through the default trust store fails with an unknown-key result. This is safer than shipping an example/test key that could later be mistaken for production trust.

## Safety boundary

A successful trust review means only `AUTHENTIC_REVIEW_READY_NOT_STAGED`. `stagingAllowed()` remains hard-false. This trust layer does **not**:

- stage or install an OTA;
- call Android recovery/update-engine installation APIs;
- reboot a device;
- write partitions or block devices;
- unlock a bootloader;
- enable SwirRoot;
- satisfy any physical-device, boot, rollback or beta gate by itself.

Those capabilities remain blocked until the repository has reproducible OS build evidence, a real boot path, safe rollback/recovery evidence and a physically verified supported device profile.

## Verification

`OtaTrustStoreHostTest` covers active, unknown, retired, revoked and wrong-channel keys, deterministic registry hashing, package/manifest binding, signature tampering, duplicate IDs, malformed IDs, SPKI mismatch, `UNKNOWN` channel rejection and non-RSA key rejection. The Essential source suite compiles and runs both the original updater policy tests and the trust-store lifecycle tests on every relevant pull request and `main` push.
