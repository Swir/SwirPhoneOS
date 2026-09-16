# SwirPhoneOS AOSP product source

This directory contains the checked-in Android integration source for the pinned Android 17 baseline. It is **source, not build or boot evidence**.

The current developer target is:

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m
```

The product inherits the standard AOSP x86_64-only Cuttlefish phone definition and keeps platform security/signing defaults intact. `swirphoneos_cf_x86_64.mk` now includes the first first-party Android module, **SwirCalculator**.

`apps/SwirCalculator/` contains a permission-free AOSP `android_app`, a pure-Java calculator engine, an original SwirPhoneOS icon/UI and localized Android resources. Its checked-in state is `ANDROID_SOURCE`, not `ANDROID_RUNTIME`.

`stage_manifest.json` is the explicit source allowlist used by `python -m swirphoneos stage-product`. It may stage files only under `vendor/swir/` and is validated for bounded size, safe relative paths and unique destinations.

A successful Kati/Soong build must be followed by Cuttlefish runtime evidence, including `sys.boot_completed=1` and application launch validation, before any runtime or roadmap completion claim is made.
