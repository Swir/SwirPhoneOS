# Reproducible AOSP build workspace

SwirPhoneOS pins Android 17 / API 37 at exact revision `android-17.0.0_r1`. A pinned baseline and checked-in source are not the same thing as a completed Android build.

## 1. Host preflight

Run on the intended Linux x86-64 builder:

```bash
python -m swirphoneos build-preflight --workspace /path/to/aosp
```

This is read-only: it installs nothing, initializes nothing and downloads nothing.

## 2. Generate the exact-tag plan

```bash
python -m swirphoneos aosp-plan --workspace /path/to/aosp --jobs 16
```

The plan records the official manifest, pinned revision, Repo init/sync commands, resolved-manifest capture, explicit source staging and Cuttlefish build command. It always reports `device_write_allowed: false`, `build_verified: false` and `boot_verified: false`.

## 3. Sync and preserve immutable source evidence

After using the generated exact-tag Repo commands on a dedicated build host:

```bash
repo manifest -r -o swirphoneos-pinned-manifest.xml
python -m swirphoneos aosp-manifest --file swirphoneos-pinned-manifest.xml
```

Every project must resolve to a full 40-character Git SHA. Preserve the manifest, SHA-256 digest, Repo/Git/JDK/host versions and complete build log.

## 4. Stage the SwirPhoneOS source bundle

Dry-run first:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp
```

Then, only inside an initialized AOSP checkout:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp --execute
```

Staging is driven by `platform/aosp_product/stage_manifest.json`. Every source and destination is explicit; destination paths must stay under `vendor/swir/`; traversal, duplicate paths, symlink sources, missing files and oversized bundles are rejected. The current bundle stages the Swir product definition plus the source/resources required to build SwirCalculator. It never uses a recursive arbitrary copy and never communicates with a phone.

## 5. Validate checked-in Android application source

Before starting a full AOSP build:

```bash
python -m swirphoneos android-apps
```

The current validator checks SwirCalculator package identity, AOSP module contract, `PRODUCT_PACKAGES` integration, permission-free manifest, RTL/backup policy, Java package identity, forbidden process/network/root primitives, eight locale catalogs and complete stage coverage. Its result is `SOURCE_READY_NOT_BUILT`; it is not APK/runtime evidence.

## 6. Build

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m -j16
```

A successful host command is build evidence only after its outputs/logs are preserved. It is not emulator-boot evidence.

## 7. Boot evidence

Launch Cuttlefish from the produced artifacts and record at minimum `sys.boot_completed=1`, SystemUI/Settings usability, SwirCalculator package/activity runtime and regression results. Only verified runtime may move an app from `ANDROID_SOURCE` toward `ANDROID_RUNTIME` or advance emulator-gate evidence.

## Safety boundary

These tools operate on an owner-controlled build workspace. They do not unlock, erase, boot, flash, root, relock or restore a phone. Physical installation remains device-profile-specific and requires separate rollback/recovery evidence. SwirRoot stays unavailable until exact-build boot/update/recovery contracts are verified.
