# AOSP source checkout integrity

SwirPhoneOS treats a resolved `repo manifest -r` snapshot as necessary but not sufficient build provenance. A persistent self-hosted workspace can contain local Git modifications even when the manifest still names exact upstream commits. The source-integrity layer closes that gap without modifying the checkout.

## What the collector proves

Run the collector only after a successful exact-tag Repo synchronization and after writing the resolved manifest snapshot:

```sh
python -m swirphoneos.aosp_source_evidence \
  --workspace /absolute/path/to/aosp \
  --manifest /absolute/path/to/aosp/swirphoneos-pinned-manifest.xml \
  > source-prebuild-evidence.json
```

For every project in the resolved manifest, the collector requires:

- a safe relative project path inside the selected AOSP workspace;
- a real Git worktree at that exact path, without a symlinked project path;
- `HEAD` exactly equal to the manifest's pinned 40-character commit;
- no tracked index/worktree difference from `HEAD`;
- no non-ignored untracked source, except an exact nested Repo project from the same manifest;
- one unchanged, bounded Git executable identity for the capture.

The report binds the exact manifest bytes, workspace identity, project inventory, commit identities and Git executable bytes with SHA-256. Successful collection records `source_checkout_verified=true`, but deliberately keeps `build_verified=false`, `boot_verified=false`, `device_write_allowed=false` and `status_promotion_performed=false`.

The collector executes only these read-only Git query families: `rev-parse`, `diff --quiet --no-ext-diff HEAD --`, and `ls-files --others --exclude-standard -z`. It does not invoke `repo sync`, `checkout`, `reset`, `clean`, build commands, Android SDK device commands or any physical-device write operation.

## Build-window continuity

For an evidence-producing AOSP build, capture the same source evidence again after the build and post-build Swir staging verification. Then bind it to the completed AOSP run:

```sh
python -m swirphoneos.aosp_source_trust_bundle \
  --run-evidence /absolute/path/to/aosp-run-evidence.json \
  --resolved-manifest-evidence /absolute/path/to/resolved-manifest.json \
  --source-pre /absolute/path/to/source-prebuild-evidence.json \
  --source-post /absolute/path/to/source-postbuild-evidence.json \
  > source-trust-bundle.json
```

The trust bundle fails closed unless both source captures refer to the exact workspace and exact resolved manifest already bound by the AOSP run, cover the complete project count, remain clean, have identical aggregate project state, and use the same exact Git executable identity. It also re-hashes the exact `resolved-manifest.json` bytes that the run evidence already recorded.

A valid source trust bundle means **clean exact Git source continuity around the host-side build window**. It does not prove that Cuttlefish booted, that any phone is supported, that installation/rollback is safe, that SwirRoot works, or that a beta gate passed.

## Failure handling

Do not repair an evidence workspace by silently running `git reset`, `git clean`, changing the manifest, broadening untracked-file exceptions or weakening the exact-commit check. A failed source-integrity capture is a real provenance failure. Inspect the dedicated builder/workspace, restore it through the normal reviewed source preparation process, and start a new evidence-producing run.

Never put credentials, serial numbers, IMEI values or private signing material into source-integrity evidence.
