# AOSP post-run artifact continuity

SwirPhoneOS has a fail-closed, read-only post-run check for the exact AOSP image bytes retained on the dedicated builder. It closes a provenance gap between the original `build-evidence.json` capture and the end of the evidence workflow: a successful build or runtime review is not accepted as proof that the retained image files stayed unchanged afterward.

## What is bound

The continuity verifier requires the immutable `aosp-run-evidence.json` and `build-evidence.json` from the same successful AOSP workflow run plus the same dedicated AOSP workspace. It verifies:

- the exact triggering Git commit matches the source commit bound into the completed AOSP run;
- the raw `build-evidence.json` bytes match the SHA-256 already bound by `aosp-run-evidence.json`;
- the canonical AOSP workspace identity matches the run evidence;
- the exact build fingerprint is consistent between run and build evidence;
- the complete reviewed build-artifact inventory contains the mandatory `boot.img` and `system.img` and only known artifact names;
- every retained artifact is still a regular non-symlink file inside the expected product output directory;
- every retained artifact still has exactly the recorded size and SHA-256;
- files do not change while they are being re-read.

The resulting `aosp-artifact-continuity.json` contains only bounded identities and relative artifact names. It does not expose the builder's raw workspace path.

## Workflow

`.github/workflows/aosp-postrun-artifact-continuity.yml` is triggered only after the `AOSP build evidence` workflow completes successfully. It runs on the same `swir-aosp-builder` concurrency group, checks out the triggering source commit, downloads that run's immutable evidence artifact, and re-opens the retained product images from `SWIR_AOSP_WORKSPACE`.

A changed, missing, replaced, symlinked or cross-run artifact causes the post-run workflow to fail closed. If a different AOSP run has already reused or cleaned the workspace, continuity also fails rather than silently accepting unrelated bytes.

Manual equivalent:

```bash
PYTHONPATH=/absolute/path/to/SwirPhoneOS python -m swirphoneos.aosp_artifact_continuity \
  --workspace /absolute/path/to/aosp \
  --run-evidence /absolute/path/to/aosp-run-evidence.json \
  --build-evidence /absolute/path/to/build-evidence.json \
  --source-commit 0123456789abcdef0123456789abcdef01234567
```

## Safety boundary

This layer is read-only. It does not build Android, launch or stop Cuttlefish, install packages, mutate the AOSP workspace, write to a phone, flash partitions, unlock a bootloader, enable SwirRoot, publish a release or promote project status. `device_write_allowed`, `physical_device_support_claimed`, `status_promotion_performed` and `release_artifact_authorized` remain `false`.

Passing continuity proves only that the locally retained artifact bytes still match the exact build evidence already bound to that run. It does **not** prove a physical-device boot, Treble/VTS compatibility, installation/rollback safety, root support or beta readiness. Weighted project progress therefore remains unchanged until the real milestone evidence exists.
