# SwirPhoneOS AOSP Build and Cuttlefish Runtime Evidence

SwirPhoneOS does not promote Android application or platform status from source presence alone. Runtime claims require evidence from the exact built product, and the runtime fingerprint must be bound back to the hashed build output.

## Build evidence

After a real `swirphoneos_cf_x86_64-aosp_current-userdebug` build, capture the exact resolved manifest and hash the product output:

```sh
repo manifest -r -o swirphoneos-pinned-manifest.xml
python -m swirphoneos build-evidence \
  --workspace /absolute/path/to/aosp \
  --manifest /absolute/path/to/aosp/swirphoneos-pinned-manifest.xml \
  --baseline platform/aosp_baseline.json > build-evidence.json
```

`build-evidence` is fail-closed. It requires an initialized AOSP checkout, a fully pinned `repo manifest -r`, the expected `out/target/product/swirphoneos_cf_x86_64` directory, non-empty `boot.img` and `system.img`, a readable system `build.prop`, and a complete fingerprint/build-id/release/API/build-type identity. It hashes the core product artifacts that exist in the reviewed allowlist. It never writes to a phone and never promotes project status.

## Runtime evidence

The `cuttlefish-evidence` command is a strict read-only collector for exactly one local emulator/Cuttlefish ADB transport. A complete report now requires:

- `sys.boot_completed=1`;
- `ro.product.name=swirphoneos_cf_x86_64`;
- `ro.product.device=vsoc_x86_64_only`;
- `ro.product.manufacturer=Swir`;
- Android release `17`, API `37` and build type `userdebug`;
- a non-empty build ID and build fingerprint plus its SHA-256 identity;
- every application currently marked `ANDROID_SOURCE` to be installed;
- every source-ready package to resolve a launcher activity inside its own package.

Capture it with an absolute trusted SDK path:

```sh
python -m swirphoneos cuttlefish-evidence --adb /absolute/path/to/adb > runtime-evidence.json
```

The collector does **not** install applications, launch activities, mutate packages, reboot, root, flash, change settings, promote registry states or establish physical-device support.

## Bind build and runtime

Once both reports are complete, bind them into one tamper-evident review object:

```sh
python -m swirphoneos evidence-bundle \
  --build build-evidence.json \
  --runtime runtime-evidence.json > evidence-bundle.json
```

The bundle is rejected unless both reports are complete, both target the exact SwirPhoneOS Cuttlefish product, and the runtime fingerprint exactly equals the fingerprint extracted from the hashed AOSP build output. The bundle adds a canonical SHA-256 over the complete build/runtime payload. This makes later editing detectable, but it does not by itself prove that every app feature was interactively tested.

## Dedicated build-host workflow

`.github/workflows/aosp-build-evidence.yml` is manual-only and targets a dedicated self-hosted runner labeled `swir-aosp-builder`. The runner must expose `SWIR_AOSP_WORKSPACE` as an absolute path to its AOSP workspace and have the Android `repo` tool/build prerequisites installed. The workflow performs exact-tag init/sync, preserves `repo manifest -r`, stages only reviewed `vendor/swir/` source, builds the Cuttlefish target, captures build evidence, and can optionally bind evidence from an already-running local Cuttlefish instance.

The workflow does not run on ordinary pushes or pull requests and does not flash physical hardware.

## Promotion evidence still required

Before a source-ready app can be considered `ANDROID_RUNTIME`, preserve and review together:

1. the exact SwirPhoneOS repository commit;
2. the resolved `repo manifest -r` snapshot and SHA-256;
3. successful Kati/Soong build logs and host/toolchain versions;
4. `build-evidence.json` with image hashes and build fingerprint;
5. Cuttlefish launch details and `runtime-evidence.json`;
6. `evidence-bundle.json` proving exact fingerprint continuity;
7. app-level interactive smoke results for the capability being claimed.

Only reviewed evidence should update the registry. The tooling intentionally never edits `system_apps/manifest.json` automatically.

## Trust boundary

Cuttlefish runtime evidence is emulator evidence, not hardware evidence. It cannot certify telephony, modem, camera, audio, sensors, charging, suspend, encryption, recovery or installation on the OnePlus Nord AC2003 or any other physical phone.
