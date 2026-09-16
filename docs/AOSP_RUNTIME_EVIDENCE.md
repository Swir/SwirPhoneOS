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

The `cuttlefish-evidence` command is a strict read-only collector for exactly one local emulator/Cuttlefish ADB transport. A complete report requires:

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

The read-only collector does **not** install applications, launch activities, mutate packages, reboot, root, flash, change settings, promote registry states or establish physical-device support.

## Emulator-only app launch smoke

Source presence plus launcher resolution is not enough to show that Android can actually start an application. After complete exact-identity runtime evidence exists, run:

```sh
python -m swirphoneos.cuttlefish_smoke \
  --adb /absolute/path/to/adb \
  --manifest system_apps/manifest.json > app-smoke-evidence.json
```

This command is intentionally more privileged than `cuttlefish-evidence`, but its scope is narrow. It first reruns the exact SwirPhoneOS Cuttlefish identity gate. Only then may it use `am start -W -n` for package-local launcher components of applications marked source-ready. For every app it requires Android to report `Status: ok` and then requires `dumpsys activity activities` to confirm that the expected app is the resumed foreground activity.

The smoke runner accepts only one local emulator-style ADB transport. It rejects network/physical-device transports and does not expose a general shell. Its command allowlist does not permit package installation, uninstall, root, reboot, flash, erase, settings changes or arbitrary commands. Launching an already-installed activity changes transient emulator foreground state, so the resulting report records that runtime-state mutation explicitly. It still never promotes `system_apps/manifest.json` automatically and is not physical-device evidence.

## Bind build and runtime

Once build and read-only runtime reports are complete, bind them into one tamper-evident review object:

```sh
python -m swirphoneos evidence-bundle \
  --build build-evidence.json \
  --runtime runtime-evidence.json > evidence-bundle.json
```

The bundle is rejected unless both reports are complete, both target the exact SwirPhoneOS Cuttlefish product, and the runtime fingerprint exactly equals the fingerprint extracted from the hashed AOSP build output. The bundle adds a canonical SHA-256 over the complete build/runtime payload. Preserve `app-smoke-evidence.json` beside that bundle; smoke success is an additional review input, not a replacement for fingerprint continuity.

## Dedicated build-host workflow

`.github/workflows/aosp-build-evidence.yml` is manual-only and targets a dedicated self-hosted runner labeled `swir-aosp-builder`. The runner must expose `SWIR_AOSP_WORKSPACE` as an absolute path to its AOSP workspace and have the Android `repo` tool, Android build prerequisites, Cuttlefish host prerequisites and a trusted absolute `adb` path installed.

The workflow performs exact-tag init/sync, preserves `repo manifest -r`, stages only reviewed `vendor/swir/` source, builds the Cuttlefish target and captures build evidence. When `collect_runtime=true`, it now also:

1. sources the exact built product environment and launches that local Cuttlefish with `launch_cvd --daemon --report_anonymous_usage_stats=n`;
2. polls the strict collector for up to six minutes until exact identity, `sys.boot_completed=1`, packages and launcher resolution are all complete;
3. preserves `runtime-evidence.json`;
4. launches every source-ready app through the emulator-only smoke allowlist and preserves `app-smoke-evidence.json`;
5. creates `evidence-bundle.json` for build/runtime fingerprint continuity;
6. runs `stop_cvd` in an `always()` cleanup step using the isolated workflow HOME.

The workflow does not run on ordinary pushes or pull requests, does not install Cuttlefish host packages itself, does not use `sudo`, and does not flash physical hardware. Runtime collection fails closed if the dedicated builder cannot provide exactly one accepted local emulator transport.

## Promotion evidence still required

Before a source-ready app can be considered `ANDROID_RUNTIME`, preserve and review together:

1. the exact SwirPhoneOS repository commit;
2. the resolved `repo manifest -r` snapshot and SHA-256;
3. successful Kati/Soong build logs and host/toolchain versions;
4. `build-evidence.json` with image hashes and build fingerprint;
5. exact-product Cuttlefish launch plus `runtime-evidence.json`;
6. `evidence-bundle.json` proving exact fingerprint continuity;
7. `app-smoke-evidence.json` proving every source-ready launcher can start and remain foreground;
8. focused interactive tests for each capability being claimed, including accessibility and locale/RTL checks where relevant.

Only reviewed evidence should update the registry. The tooling intentionally never edits `system_apps/manifest.json` automatically.

## Trust boundary

Cuttlefish runtime and app-launch evidence are emulator evidence, not hardware evidence. They cannot certify telephony, modem, camera, audio, sensors, charging, suspend, encryption, recovery or installation on the OnePlus Nord AC2003 or any other physical phone.
