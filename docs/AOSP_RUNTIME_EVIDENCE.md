# SwirPhoneOS Cuttlefish Runtime Evidence

SwirPhoneOS does not promote Android application or platform status from source presence alone. Runtime claims require evidence from the exact built product.

## Scope

The `cuttlefish-evidence` command is a strict read-only collector for one local emulator/Cuttlefish ADB transport. It verifies the minimum runtime facts needed after a real `swirphoneos_cf_x86_64-aosp_current-userdebug` build:

- `sys.boot_completed=1`;
- `ro.product.name=swirphoneos_cf_x86_64`;
- a non-empty build fingerprint and its SHA-256 identity;
- reported Android release, security patch and locale;
- presence of every application that is currently marked `ANDROID_SOURCE` in `system_apps/manifest.json`.

The collector does **not** install applications, mutate packages, reboot, root, flash, change settings, promote registry states or establish physical-device support.

## Capture

Use a trusted Android SDK `adb` executable by absolute path and connect exactly one local Cuttlefish/emulator transport:

```sh
python -m swirphoneos cuttlefish-evidence --adb /absolute/path/to/adb
```

The output is JSON. `runtime_evidence_complete=true` means only that the reviewed minimum checks passed for that running local instance. It is not sufficient on its own to mark `ANDROID_RUNTIME`.

## Evidence bundle required for promotion

Before a source-ready app can be considered `ANDROID_RUNTIME`, preserve and review together:

1. the exact SwirPhoneOS repository commit;
2. the resolved `repo manifest -r` snapshot and SHA-256;
3. host/toolchain versions and successful Kati/Soong build logs;
4. the produced image/artifact checksums;
5. Cuttlefish launch details and `cuttlefish-evidence` JSON;
6. app-level smoke results for the capability being claimed.

Only reviewed evidence should update the registry. The tooling intentionally never edits `system_apps/manifest.json` automatically.

## Trust boundary

Cuttlefish runtime evidence is emulator evidence, not hardware evidence. It cannot certify telephony, modem, camera, audio, sensors, charging, suspend, encryption, recovery or installation on the OnePlus Nord AC2003 or any other physical phone.
