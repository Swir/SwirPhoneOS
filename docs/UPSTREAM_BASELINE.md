# AOSP Upstream Baseline

Checked: **2026-09-16**. This document records a reproducibility pin and build policy; it is not evidence of a completed Android build.

## Current pinned candidate

Official AOSP documentation currently recommends the moving `android-latest-release` manifest for upstream development. At the checked date it resolves to `android17-release`. The AOSP build-number table lists Android 17 / API 37 and release tag `android-17.0.0_r1`, build ID `CP2A.260605.016`, with security patch level `2026-06-05`.

SwirPhoneOS now preserves the exact official manifest identity for that release tag:

| Field | Pinned value |
| --- | --- |
| Repo init revision | `android-17.0.0_r1` |
| Annotated tag object | `7a9e46ba6ed424f922a3457f4964e67e0b966201` |
| Manifest commit | `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f` |
| Manifest tree | `1541b7154f1532032baf7c73f222256cc29e8cfb` |
| Build ID | `CP2A.260605.016` |
| API level | `37` |

`platform/aosp_baseline.json` is therefore **`PINNED_NOT_BUILT`**, not `CANDIDATE_NOT_PINNED`. This removes a moving-reference ambiguity but does **not** complete the AOSP milestone. No source sync or Android build has been performed by this repository automation.

Primary references:

- https://source.android.com/docs/whatsnew/site-updates
- https://source.android.com/docs/setup/reference/build-numbers
- https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1

## Reproducibility contract

The exact tag pin is only the first lock. Before the `aosp_baseline` milestone can complete, the project must:

1. initialize Repo from the official Android manifest repository at the exact `android-17.0.0_r1` revision;
2. sync the complete source tree in a controlled build workspace;
3. preserve the resolved `repo manifest -r` output so every project revision is recorded rather than relying only on the top-level manifest commit;
4. record a SHA-256 for that resolved manifest plus Repo/Git/JDK/build-host versions;
5. record required proprietary/vendor inputs separately and verify their legal source;
6. complete the platform build and preserve logs, artifact hashes and the exact SwirPhoneOS candidate commit;
7. repeat the build from the preserved metadata before calling the result reproducible.

The baseline validator intentionally rejects incomplete pin metadata and prevents `BUILT_VERIFIED` from being claimed until both source acquisition and build completion are recorded.

## Build-host preflight

A bounded read-only preflight is now implemented as:

```sh
python -m swirphoneos build-preflight --workspace /absolute/path/to/workspace
```

It checks host/architecture, glibc, free workspace capacity, RAM visibility, required `git`/`repo` commands and reports KVM availability. It does **not** install packages, download source, configure Cuttlefish/KVM, alter the host or start a build.

The current conservative full-build floor follows the official AOSP setup guidance: 64-bit x86 Linux, glibc 2.17 or newer, at least 400 GiB free disk and at least 64 GiB RAM. Passing this preflight means only that the basic host gate is plausible; a real source sync/build is still required.

References:

- https://source.android.com/docs/setup/start
- https://source.android.com/docs/setup/start/requirements

## GSI policy

AOSP describes GSI as a generic system image for Treble-capable Android devices, but Android devices still differ in bootloader, AVB, partition, kernel/vendor and recovery behavior. SwirPhoneOS will therefore use GSI as one compatibility path, not as proof that one image or flashing sequence is safe for every phone.

Device-specific bootloader, AVB, partition, kernel/vendor and recovery requirements remain profile/port work and require physical hardware evidence.

References:

- https://source.android.com/docs/core/tests/vts/gsi
- https://source.android.com/docs/core/architecture/bootloader/locking_unlocking

## Next platform gate

The next safe platform task is a controlled source sync at the exact pinned release tag in a host that passes preflight, followed by preservation of `repo manifest -r`, toolchain/host metadata and the first reproducible platform build attempt. Emulator/Cuttlefish boot comes only after a successful built product exists.
