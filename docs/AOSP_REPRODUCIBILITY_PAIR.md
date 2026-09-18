# AOSP reproducibility pair evidence

SwirPhoneOS treats reproducibility as an evidence problem, not as a CI badge. The repository includes a read-only comparator that can bind **two independently completed AOSP build runs** to the same reviewed source inputs and then require the complete retained artifact inventories to match byte-for-byte.

This is one observation in the reproducible-build program. A single matching pair does **not** by itself complete the `aosp_baseline` milestone, pass a beta gate, authorize a release, prove device support, or prove install/rollback safety.

## Inputs

The comparator consumes four immutable JSON reports:

1. `aosp-run-evidence.json` from independent build run A.
2. `aosp-artifact-continuity.json` from the post-run continuity workflow for run A.
3. `aosp-run-evidence.json` from independent build run B.
4. `aosp-artifact-continuity.json` from the post-run continuity workflow for run B.

Both run reports must bind the same exact SwirPhoneOS source commit, resolved Repo-manifest file digest, staged `vendor/swir` content digest, system-app manifest digest, source-ready package set and Android build fingerprint. Each continuity report must independently validate and must bind the exact bytes of its corresponding run report, workspace identity, build-evidence file and retained artifact inventory.

The two run IDs must be different. The manual GitHub Actions workflow also requires two different post-run continuity workflow IDs. This prevents one completed run from being supplied twice and misrepresented as an independent pair.

## Byte-for-byte requirement

The full retained artifact list must match between both runs. Path, size and SHA-256 must be identical for every retained artifact, including the required `boot.img` and `system.img` images. Optional reviewed artifacts are part of the comparison when present; a missing/extra artifact therefore fails the pair instead of silently reducing the scope.

Evidence files are strict UTF-8 JSON, duplicate JSON keys are rejected, input files must be regular non-symlink files, canonical report digests are checked, and cross-run or cross-report substitution fails closed.

## Running locally

```bash
python -m swirphoneos.aosp_reproducibility \
  --run-a /absolute/path/run-a/aosp-run-evidence.json \
  --continuity-a /absolute/path/run-a/aosp-artifact-continuity.json \
  --run-b /absolute/path/run-b/aosp-run-evidence.json \
  --continuity-b /absolute/path/run-b/aosp-artifact-continuity.json \
  --source-commit <exact-40-character-git-sha>
```

A successful comparison emits `local_aosp_reproducibility_pair_evidence` with `reproducibility_observation: MATCHING_PAIR`. The output explicitly keeps `milestone_promoted`, `beta_gate_passed`, `release_artifact_authorized`, `device_write_allowed`, `physical_device_support_claimed` and `status_promotion_performed` false.

## GitHub Actions workflow

`AOSP reproducibility pair evidence` is a manual, read-only workflow. Supply:

- the exact shared source SHA;
- the AOSP build-evidence workflow run ID for run A;
- the matching post-run continuity workflow run ID for run A;
- the AOSP build-evidence workflow run ID for run B;
- the matching post-run continuity workflow run ID for run B.

The workflow uses only `actions: read` and `contents: read`, downloads immutable evidence from the selected runs, checks out the exact source SHA, runs the comparator, and uploads only the bounded `aosp-reproducibility-pair.json` result. It contains no ADB reboot, Fastboot write, Repo sync, Cuttlefish launch, flashing, root, unroot, device mutation or release operation.

## What this does not prove

A matching pair does not prove that Android boots, that Cuttlefish runtime checks passed, that UI/RTL/accessibility reviews passed, or that a physical phone is supported. It also does not prove safe flashing, stock restore, OTA rollback, telephony, camera, root/unroot or beta readiness. Those remain separate evidence domains and separate project gates.
