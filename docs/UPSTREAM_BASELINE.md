# AOSP Upstream Baseline

Checked: **2026-09-16**. This document records discovery only; it is not evidence of a completed Android build.

## Current candidate

Official AOSP documentation currently recommends the moving `android-latest-release` manifest for AOSP development. At the checked date it resolves to the `android17-release` release branch. The AOSP build-number table lists Android 17 / API 37 and the release tag `android-17.0.0_r1` with build ID `CP2A.260605.016` and security patch level `2026-06-05`.

SwirPhoneOS therefore records Android 17 as the current **baseline candidate**, while keeping `platform/aosp_baseline.json` at `CANDIDATE_NOT_PINNED`.

Primary references:

- https://source.android.com/docs/whatsnew/site-updates
- https://source.android.com/docs/setup/reference/build-numbers
- https://android.googlesource.com/platform/manifest

## Why `android-latest-release` is not our reproducible pin

`android-latest-release` intentionally tracks the newest AOSP release branch. That is useful for discovery and upstream development, but a moving reference is insufficient for a reproducible SwirPhoneOS release.

Before the `aosp_baseline` milestone can move forward, the project must:

1. select an exact release candidate/tag after compatibility review;
2. initialize the AOSP manifest from the official Android manifest repository;
3. resolve every project revision and preserve a revision-locked manifest snapshot (for example, the equivalent of `repo manifest -r` after sync);
4. record the manifest snapshot SHA-256 plus Repo/Git/JDK/build-host versions;
5. record required proprietary/vendor inputs separately and verify their legal source;
6. complete the platform build and preserve build logs, artifact hashes and exact candidate commit;
7. repeat the build from the preserved metadata before calling it reproducible.

No source sync has been started by this repository automation, and no Android image has been built.

## GSI policy

AOSP describes GSI as a generic system image for Treble-capable Android devices, but the same official guidance states that Android devices have different designs and there is no single generic flashing command or instruction set that applies to all devices.

SwirPhoneOS will use GSI as one compatibility path, not as proof that one image or installer is safe for every phone. Device-specific bootloader, AVB, partition, kernel/vendor and recovery requirements remain profile/port work and require hardware evidence.

References:

- https://source.android.com/docs/core/tests/vts/gsi
- https://source.android.com/docs/core/architecture/bootloader/locking_unlocking

## Build-resource gate

Before any large AOSP source download is started, re-check the official AOSP build-environment requirements in `docs/SOURCES.md`, confirm adequate disk/RAM/CPU capacity and choose the build host intentionally. A bounded preflight should fail before downloading hundreds of gigabytes when the environment is unsuitable.

The next safe platform task is an **offline build-host preflight and reproducibility manifest design**, not an unbounded automatic source sync.
