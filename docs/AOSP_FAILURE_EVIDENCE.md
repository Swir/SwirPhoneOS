# AOSP failure evidence

SwirPhoneOS treats the first real Android build as an evidence-producing engineering run, including when the run fails. A failed self-hosted build must leave enough bounded, integrity-addressed information to identify the failed phase and continue debugging without weakening the pinned baseline or inventing build/runtime success.

## Scope

`swirphoneos.aosp_failure_evidence` is read-only. It does not retry Repo, invoke Kati/Soong/Ninja, launch Cuttlefish, alter the AOSP workspace, install packages, or access a phone. It hashes files that already exist in the GitHub Actions workspace and optionally hashes a bounded build-log tail.

The dedicated workflow records a phase marker before each high-impact stage:

`BOOTSTRAP` → `TOOLCHAIN` → `PREFLIGHT` → `SOURCE_SYNC` → `SOURCE_STAGE` → `BUILD` → `POST_BUILD_STAGE` → `BUILD_EVIDENCE` → optional `RUNTIME_LAUNCH` → `RUNTIME_WAIT` → `APP_SMOKE` → `RUNTIME_BIND` → `RUN_BIND`.

A failure report uses only one of those reviewed values. Arbitrary phase names are rejected.

## Bounded diagnostics

The workflow creates `aosp-run-context.txt` before checkout so an artifact can survive failures that happen before Python tooling is available. The file contains only the workflow source commit plus the requested parallel-job count and runtime-collection flag; it intentionally excludes secrets, environment dumps and host paths.

During the AOSP build, console output is streamed to the normal GitHub Actions log and a temporary local file. On build failure, only the final **256 KiB** is retained as `aosp-build-tail.log`; the temporary full copy is deleted. On success, both local build-log files are deleted. A later always/failure collection step also bounds a leftover temporary log if the build step is interrupted after the file was created.

`aosp-failure-evidence.json` records:

- the exact 40-character workflow source commit;
- the failed reviewed phase;
- the pinned Android baseline identity;
- presence, file name, byte length and SHA-256 for each requested evidence file that exists;
- explicit missing state for evidence files that were not reached;
- presence/size/SHA-256 for the bounded diagnostic tail;
- one phase-specific next action;
- a canonical SHA-256 over the complete report content except the digest field itself.

Input evidence files are capped at 16 MiB each, the diagnostic tail is capped at 256 KiB, and symbolic links/non-regular files are rejected. The report does not parse a partially written upstream evidence JSON and therefore does not accidentally trust a failed phase's claims; it only inventories and hashes the bytes that existed at failure time.

## Safety semantics

Every failure report is permanently `FAILED_NOT_READY`. The following fields are required to remain `false`:

- `build_succeeded`
- `runtime_succeeded`
- `status_promotion_allowed`
- `device_write_allowed`
- `flash_allowed`
- `root_allowed`

The report is **not** evidence of a successful build, boot, app runtime, supported phone, safe installation, recovery, SwirRoot support or beta readiness. A missing report is never interpreted as success. If the failure-evidence generator itself cannot run, the workflow preserves `aosp-run-context.txt`, `aosp-phase.txt`, GitHub step logs and a small `aosp-failure-evidence-error.txt` marker instead.

## Why this matters

The current project blocker is the first complete `android-17.0.0_r1` sync/build/boot on the dedicated Linux builder. A failure at Repo, source staging, Kati/Soong/Ninja, provenance collection or Cuttlefish should produce a reviewable artifact rather than forcing the next iteration to guess which gate failed. The correct response is to fix the earliest reproducible failure while preserving exact release/build identity and evidence continuity, not to relax checks merely to make CI green.
