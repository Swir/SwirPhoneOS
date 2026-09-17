# AOSP Builder Evidence Hardening

SwirPhoneOS treats a successful Android build as an evidence-producing operation, not as proof of phone compatibility. The manual self-hosted `AOSP build evidence` workflow is intentionally fail-closed and remains separate from physical-device installation.

## Builder preflight gate

Before `repo init` or `repo sync`, the workflow writes `builder-preflight.json` and requires `ready_for_full_build=true`. The preflight checks the dedicated Linux x86-64 host, required `git`/`repo` commands, glibc baseline, RAM and free workspace capacity. If runtime evidence is requested, writable/readable KVM is an additional mandatory gate. A failed preflight stops before source synchronization while preserving the preflight report as a workflow artifact when possible.

The workflow consumes the actual preflight schema (`checks[].id` and `checks[].passed`) and also rejects an internally inconsistent report where the aggregate build-ready flag is true while an individual mandatory check is false. This keeps the expensive source-sync/build path tied to the same contract exercised by host CI.

This does not prove that every AOSP host package or driver is correct. It prevents known-insufficient hosts from spending hours on a source sync/build that cannot satisfy the repository's documented minimum contract.

## Exact staged-source evidence

`stage-product` schema v5 records every manifest-whitelisted SwirPhoneOS source file with its repository-relative source, AOSP-relative destination, exact byte size and SHA-256. A canonical `staged_content_sha256` binds the complete destination/size/hash set.

A persistent self-hosted AOSP checkout can retain files from an older SwirPhoneOS revision even after those files are removed from the current staging manifest. Schema v5 closes that reproducibility gap. Before copying, `stage-product --execute` inventories the entire regular-file set under `vendor/swir/` without following symlinks. Any pre-existing file that is not an exact destination in the current reviewed manifest causes a fail-closed error. The tool does **not** silently delete or rewrite an unreviewed stale file; the operator must inspect and deliberately clean the workspace before retrying.

When `--execute` is used, staging creates destination directories without following a pre-existing symlink chain, rejects symlink/non-file destinations, copies the source, then re-reads the destination and requires the copied size and SHA-256 to match the pre-copy source evidence. It inventories `vendor/swir/` again after copying and requires the resulting regular-file set to equal the current manifest destinations exactly. The report records `preexisting_destination_file_count`, `destination_file_count` and `destination_tree_closed=true` only after that closure proof succeeds.

The self-hosted build workflow rejects any stage report that is not schema v5, fully executed, fully copy-verified, exact-count closed and backed by a valid 64-character bundle digest. This gate runs before Kati/Soong compilation.

## Post-build source immutability and closure proof

A successful compile is followed by `python -m swirphoneos.stage_evidence`. It reopens the persisted stage report, requires the same initialized AOSP workspace, and then re-reads every recorded destination under `vendor/swir/`. Every file must still be a regular non-symlink path and must still match the exact pre-build size and SHA-256.

The verifier then independently inventories the complete `vendor/swir/` regular-file tree. The actual file set must still equal the reviewed stage-report destinations exactly. A generated, stale or otherwise unreviewed extra file therefore fails the run even if all originally staged files are still byte-identical.

If any staged source file changes, disappears, is replaced by a symlink, escapes the reviewed destination tree, or the tree gains an unreviewed file, the workflow fails before build provenance is accepted. A successful check emits `post-build-stage-evidence.json` with `destination_tree_closed=true`, the exact destination file count, a separate integrity digest and the original `staged_content_sha256` for correlation.

This closes both gaps between “these bytes were staged” and “these exact staged bytes were still present when the completed build was accepted as evidence,” and between “the reviewed files are present” and “no extra unreviewed Swir source is also present.” It does not claim that the Android build itself is reproducible until repeated real builds produce matching evidence.

## Pinned build identity

`build-evidence` does not accept an arbitrary Android 17 `userdebug` output. In addition to regular non-empty core images and a fully pinned resolved Repo manifest, the built `system/build.prop` must match the exact checked-in baseline for:

- Android release;
- API level;
- build ID;
- security patch level;
- build type.

The current baseline remains `android-17.0.0_r1` / build `CP2A.260605.016` / security patch `2026-06-05`. A build with a different build ID, API, release, patch level or type is rejected rather than silently being described as the pinned candidate.

## Complete run evidence chain

`python -m swirphoneos aosp-run-evidence` is the final host-side correlation layer for one workflow run. It accepts the exact source commit plus the already-produced JSON reports and rejects cross-run mixing.

For every build it binds:

1. builder preflight;
2. AOSP workspace/revision/lunch plan;
3. pinned resolved-manifest evidence;
4. pre-build staged-source evidence with exact `vendor/swir/` tree closure;
5. post-build staged-source byte and tree-closure re-verification;
6. exact build/artifact evidence.

When runtime collection is enabled, the runtime group is all-or-nothing and additionally binds:

7. strict Cuttlefish boot/runtime evidence;
8. source-ready application launch-smoke evidence;
9. the build/runtime evidence bundle.

The validator requires workspace/revision continuity, identical resolved-manifest identity, the same staged-source digest before and after compilation, exact destination counts and tree closure before/after build, exact pinned build identity, required `boot.img`/`system.img` hash records, exact build/runtime fingerprint continuity, the exact source-ready package set, successful package-local foreground launches and an intact canonical build/runtime bundle digest.

The resulting `aosp-run-evidence.json` contains the workflow source commit, build fingerprint hash, staged-source hash and SHA-256 of each input report. It is either `BUILD_ONLY` or `BUILD_AND_RUNTIME`; partial runtime groups are rejected. It never promotes app/platform status and never enables device writes.

## Evidence boundaries

These reports strengthen reproducibility and supply-chain review, but they do not change project readiness by themselves. They do not prove a successful AOSP build until the dedicated builder actually completes one; build-only evidence does not prove Cuttlefish boot; emulator evidence does not prove GSI compatibility, physical-device boot, safe installation/restore, telephony, camera or SwirRoot mutation support.

The repository therefore remains at the same weighted progress until the existing runtime and physical-device gates produce real evidence. No phone write, flash, unlock, root or restore action is introduced by this hardening.
