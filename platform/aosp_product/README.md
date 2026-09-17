# SwirPhoneOS AOSP product source

This directory contains the checked-in Android integration source for the pinned Android 17 baseline. It is **source, not build, boot, Treble/VTS, hardware or install evidence**.

## Developer products

The primary emulator/runtime target remains the x86_64 Cuttlefish product:

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m
```

A separate ARM64 Generic System Image developer target is now registered for broad Treble-oriented validation work:

```bash
source build/envsetup.sh
lunch swirphoneos_gsi_arm64-aosp_current-userdebug
m systemimage
```

The expected GSI artifact is `out/target/product/generic_arm64/system.img`. The GSI product inherits the standard AOSP ARM64 product plus the AOSP GSI release configuration because the upstream `aosp_arm64.mk` GSI-release block is conditional on the upstream product name. This checked-in configuration is deliberately called a **developer target**, not a universal phone image.

Both products keep Android platform security/signing defaults intact and include the complete current set of twenty first-party SwirPhoneOS application modules. Every app remains `ANDROID_SOURCE` until a real pinned build and runtime review provide stronger evidence.

Each app is a permission-bounded AOSP `android_app` with its own SwirPhoneOS icon/UI, eight locale resource catalogs (EN/PL/NB/DE/ES/FR/PT/AR), host-testable pure-Java logic/contracts where appropriate and explicit source validation. Exact permission allowlists and SwirRoot no-mutation gates remain enforced.

`stage_manifest.json` plus `stage_manifest.d/*.json` form the explicit source allowlist used by `python -m swirphoneos stage-product`. Staging may write only under `vendor/swir/`, rejects unsafe paths/symlinks/hard-link aliases and stale files, and requires exact tree closure before and after a platform build.

## Evidence boundaries

A successful Cuttlefish Kati/Soong build must still be followed by exact runtime evidence, including `sys.boot_completed=1` and application launch validation, before any `ANDROID_RUNTIME` or emulator milestone claim is made.

A successful ARM64 GSI `systemimage` build must still be followed by relevant Treble/VTS validation and explicit physical-device compatibility/recovery testing. A generic image must never automatically mark `oneplus/avicii` or any other phone as supported, and it never enables flash/root/write controls in SwirPhoneStudio.

See [`../../docs/GSI_BUILD_EVIDENCE.md`](../../docs/GSI_BUILD_EVIDENCE.md) for the GSI evidence chain and compatibility boundary.
