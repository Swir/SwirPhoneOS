# SwirPhoneOS AOSP product source

This directory contains the checked-in Android integration source for the pinned Android 17 baseline. It is **source, not build or boot evidence**.

The current developer target is:

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m
```

The product inherits the standard AOSP x86_64-only Cuttlefish phone definition and keeps platform security/signing defaults intact. `swirphoneos_cf_x86_64.mk` currently includes six first-party Android source modules: **SwirCalculator, SwirSettings, SwirFiles, SwirDeviceCare, SwirUpdate and SwirPrivacy**.

Each app is a permission-bounded AOSP `android_app` with its own SwirPhoneOS icon/UI, eight locale resource catalogs (EN/PL/NB/DE/ES/FR/PT/AR), host-testable pure-Java logic/contracts and explicit source validation. Their checked-in state is `ANDROID_SOURCE`, not `ANDROID_RUNTIME`.

SwirUpdate is intentionally read-only at this stage: it reports the local build/channel and contains host-tested SHA-256/RSA detached-signature verification primitives, but it does not download, stage or install packages and does not hand off to recovery. SwirPrivacy exposes only a reviewed allowlist of authoritative Android privacy/permission settings; platform-backed live indicators and access history are not claimed yet.

`stage_manifest.json` is the explicit source allowlist used by `python -m swirphoneos stage-product`. It may stage files only under `vendor/swir/` and is validated for bounded size, safe relative paths and unique destinations.

A successful Kati/Soong build must be followed by Cuttlefish runtime evidence, including `sys.boot_completed=1` and application launch validation, before any runtime or roadmap completion claim is made.
