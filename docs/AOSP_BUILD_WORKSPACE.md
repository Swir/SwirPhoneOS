# Reproducible AOSP build workspace

SwirPhoneOS pins Android 17 / API 37 at exact revision `android-17.0.0_r1`. A pinned baseline and checked-in source are not the same thing as a completed Android build.

## 1. Host preflight

Run on the intended Linux x86-64 builder:

```bash
python -m swirphoneos build-preflight --workspace /path/to/aosp
```

This is read-only: it installs nothing, initializes nothing and downloads nothing. The dedicated full-build contract currently requires Linux x86-64, supported glibc, `git`, `repo`, at least 64 GiB RAM and at least 400 GiB free workspace capacity. Runtime collection additionally requires usable KVM.

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

Every project must resolve to a full 40-character Git SHA. Preserve the manifest and its SHA-256 evidence. The manual builder workflow records the bounded run context and source/build evidence automatically; failures preserve only the reviewed bounded diagnostic set rather than publishing an unrestricted build log.

## 4. Stage the SwirPhoneOS source bundle

Dry-run first:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp
```

Then, only inside an initialized AOSP checkout:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp --execute
```

Staging is driven by `platform/aosp_product/stage_manifest.json` plus reviewed `stage_manifest.d/*.json` fragments. Every source and destination is explicit; destination paths must stay under `vendor/swir/`; traversal, duplicate paths, symlink sources/destinations, missing files and oversized bundles are rejected. The current bundle covers the Swir Cuttlefish product and all source/resources required by the 20 applications marked `ANDROID_SOURCE` in the system-app registry. It never uses an arbitrary recursive repository copy and never communicates with a phone.

Schema-v5 staging also protects persistent self-hosted AOSP workspaces against stale source. Before copying, the tool inventories regular files under `vendor/swir/` without following symlinks and rejects any file that is not an exact current manifest destination. It does not silently delete stale files. After copying, it requires the whole regular-file set under `vendor/swir/` to equal the current reviewed destination set exactly and records `destination_tree_closed=true` plus exact file counts.

If staging reports a stale/unreviewed file, inspect the path and deliberately clean the owner-controlled build workspace before retrying. Do not weaken or bypass the closure check to obtain a build.

## 5. Validate checked-in Android application source

Before starting a full AOSP build:

```bash
python -m swirphoneos android-apps
```

The validator currently covers all 20 source-ready applications. It checks package/module/product integration, exact per-app permission allowlists, localization parity for EN/PL/NB/DE/ES/FR/PT/AR, RTL requirements, complete bounded stage coverage and source-wide rejection of forbidden process/network/broad-storage primitives. SwirRoot receives additional fail-closed checks. Its result is source validation only; it is not APK/runtime or physical-device evidence.

## 6. Build

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m -j16
```

After a successful compile, run the post-build stage verifier before accepting build provenance:

```bash
python -m swirphoneos.stage_evidence --report /path/to/stage-report.json --workspace /path/to/aosp
```

It re-hashes every reviewed staged file and independently re-inventories the entire `vendor/swir/` regular-file tree. Any changed, missing, symlinked, generated, stale or otherwise unreviewed file fails the evidence chain. This prevents an old or build-created Swir source file from being silently included in an accepted run.

A successful host command becomes build evidence only after the exact pinned source identity, exact build identity and hashed core images are captured. It is not emulator-boot evidence.

## 7. Boot and application evidence

The manual `AOSP build evidence` workflow can optionally launch the exact product it just built in Cuttlefish. Runtime evidence must prove `sys.boot_completed=1`, the exact SwirPhoneOS product/device/manufacturer, Android 17 / API 37, the exact build fingerprint and presence plus package-local launcher resolution for every current `ANDROID_SOURCE` app.

The emulator-only smoke runner then launches each source-ready app using its resolved package-local component, requires `am start -W` success and confirms the expected package is resumed in the foreground. Build, runtime and smoke evidence are bound into one run chain; none of these operations promotes registry status automatically.

Focused interactive checks for persistence, permissions, accessibility, locale switching, text expansion and Arabic RTL are still required before reviewing any `ANDROID_RUNTIME` promotion.

## Safety boundary

These tools operate on an owner-controlled build workspace or local emulator. They do not unlock, erase, flash, root, relock or restore a physical phone. Physical installation remains device-profile-specific and requires separate rollback/recovery and exact-hardware evidence. SwirRoot stays unavailable until exact-build boot/update/recovery contracts and a legitimate supported device path are physically verified.
