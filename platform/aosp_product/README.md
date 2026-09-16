# SwirPhoneOS AOSP product skeleton

This directory is the first checked-in Android product integration slice for the pinned Android 17 baseline. It is **not** build or boot evidence.

After syncing the exact pinned AOSP manifest, copy this directory into `device/swir/phone/` inside the AOSP workspace. Android 17 uses a product/release/variant lunch form for explicit targets, so the intended developer target is:

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m
```

The product inherits the standard AOSP x86_64-only Cuttlefish phone definition and changes only product identity at this stage. It deliberately does not disable Verified Boot/security policy, add test keys, enable root, or claim a release image.

A successful Kati/Soong build must be followed by a Cuttlefish boot and `sys.boot_completed=1` evidence before the corresponding roadmap gate can move.
