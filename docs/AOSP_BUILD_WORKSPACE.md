# Reproducible AOSP build workspace

SwirPhoneOS pins its current development baseline in `platform/aosp_baseline.json`. The current baseline is Android 17 / API 37 at the exact release revision `android-17.0.0_r1`. A pinned baseline is not the same thing as a completed Android build.

This document defines the evidence path from the checked-in baseline to the first real Cuttlefish build while keeping host-side tooling fail-closed and avoiding any phone write operation.

## 1. Host preflight

Run on the intended Linux x86-64 AOSP builder:

```bash
python -m swirphoneos build-preflight --workspace /path/to/aosp
```

The command is read-only. It does not install packages, initialize Repo, download Android sources or alter the host.

## 2. Generate the exact-tag plan

```bash
python -m swirphoneos aosp-plan --workspace /path/to/aosp --jobs 16
```

The JSON output is a plan only. It must report:

- the official Android manifest repository;
- the exact pinned release revision;
- the SwirPhoneOS Cuttlefish lunch choice;
- argv-oriented Repo init/sync commands;
- the resolved-manifest capture step;
- the explicit product-staging step;
- the final Kati/Soong build command;
- `device_write_allowed: false`;
- `build_verified: false` and `boot_verified: false`.

Do not mark the AOSP roadmap gate complete from this plan.

## 3. Initialize and sync AOSP

Use the generated commands on the dedicated build host. The current contract initializes the official manifest at the exact release tag and performs a current-manifest sync. Preserve the terminal log and tool versions used for the build.

After sync, capture an immutable manifest snapshot:

```bash
repo manifest -r -o swirphoneos-pinned-manifest.xml
python -m swirphoneos aosp-manifest --file swirphoneos-pinned-manifest.xml
```

`aosp-manifest` requires every project entry to resolve to a full 40-character Git revision and returns a SHA-256 digest for the snapshot. Store the snapshot and digest with build evidence.

## 4. Stage the SwirPhoneOS product

Dry-run first:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp
```

The default mode does not write anything. To copy the two checked-in product makefiles into an already initialized AOSP checkout:

```bash
python -m swirphoneos stage-product --workspace /path/to/aosp --execute
```

The execute path refuses a directory that does not contain both `.repo/` and `build/envsetup.sh`. It copies only:

- `AndroidProducts.mk`
- `swirphoneos_cf_x86_64.mk`

into `vendor/swir/products/`. It does not modify a phone, unlock a bootloader or run Fastboot.

## 5. Build

From the synchronized AOSP checkout, the planned build path is equivalent to:

```bash
source build/envsetup.sh
lunch swirphoneos_cf_x86_64-aosp_current-userdebug
m -j16
```

A successful host command alone is not emulator-boot evidence. Preserve the complete build log, the resolved manifest snapshot/digest and the exact output artifact identities before changing platform status.

## 6. Boot evidence

The next milestone after a successful build is a real Cuttlefish boot using the produced images, with recorded runtime evidence including `sys.boot_completed=1`, basic SystemUI/Settings usability and regression results. Only then may the emulator boot gate move forward.

## Safety boundary

These tools are for an owner-controlled AOSP build workspace. They never provide a generic phone flash command. Physical installation remains device-profile-specific and requires separate recovery/rollback evidence. SwirRoot remains unavailable until exact-build boot/update/recovery contracts are sufficiently verified.
