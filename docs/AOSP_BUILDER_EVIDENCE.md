# AOSP Builder Evidence Hardening

SwirPhoneOS treats a successful Android build as an evidence-producing operation, not as proof of phone compatibility. The manual self-hosted `AOSP build evidence` workflow is intentionally fail-closed and remains separate from physical-device installation.

## Builder preflight gate

Before `repo init` or `repo sync`, the workflow writes `builder-preflight.json` and requires `ready_for_full_build=true`. The existing preflight checks the dedicated Linux x86-64 host, required `git`/`repo` commands, glibc baseline, RAM and free workspace capacity. If runtime evidence is requested, writable/readable KVM is an additional mandatory gate. A failed preflight stops before source synchronization while preserving the preflight report as a workflow artifact when possible.

This does not prove that every AOSP host package or driver is correct. It prevents known-insufficient hosts from spending hours on a source sync/build that cannot satisfy the repository's documented minimum contract.

## Exact staged-source evidence

`stage-product` schema v4 records every manifest-whitelisted SwirPhoneOS source file with its repository-relative source, AOSP-relative destination, exact byte size and SHA-256. A canonical `staged_content_sha256` binds the complete destination/size/hash set.

When `--execute` is used, staging creates destination directories without following a pre-existing symlink chain, rejects symlink/non-file destinations, copies the source, then re-reads the destination and requires the copied size and SHA-256 to match the pre-copy source evidence. Only then can `copy_verified=true` be emitted.

The self-hosted build workflow rejects any stage report that is not schema v4, fully executed, fully copy-verified and backed by a valid 64-character bundle digest. This gate runs before Kati/Soong compilation.

## Post-build source immutability proof

A successful compile is followed by `python -m swirphoneos.stage_evidence`. It reopens the persisted stage report, requires the same initialized AOSP workspace, and then re-reads every recorded destination under `vendor/swir/`. Every file must still be a regular non-symlink path and must still match the exact pre-build size and SHA-256.

If any staged source file changes, disappears, is replaced by a symlink, escapes the reviewed destination tree, or no longer matches the report, the workflow fails before build provenance is accepted. A successful check emits `post-build-stage-evidence.json` with a separate integrity digest and preserves the original `staged_content_sha256` for correlation.

This closes the gap between “these bytes were staged” and “these exact staged bytes were still present when the completed build was accepted as evidence.” It does not claim that the Android build itself is reproducible until repeated real builds produce matching evidence.

## Evidence boundaries

These reports strengthen reproducibility and supply-chain review, but they do not change project readiness by themselves. They do not prove a successful AOSP build, a Cuttlefish boot, GSI compatibility, a physical-device boot, safe installation/restore, telephony, camera or SwirRoot mutation support.

The repository therefore remains at the same weighted progress until the existing runtime and physical-device gates produce real evidence. No phone write, flash, unlock, root or restore action is introduced by this hardening.
