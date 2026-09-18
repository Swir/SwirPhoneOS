# AOSP Runtime Tool Evidence

SwirPhoneOS treats the Android SDK `adb` binary used for local Cuttlefish runtime checks as part of the reviewed evidence surface. The AOSP builder therefore records and re-verifies the exact local `adb` bytes around the runtime evidence window instead of trusting only a mutable filesystem path.

This mechanism is host-side trust evidence only. It does not build Android, launch Cuttlefish, authorize physical-device writes, unlock a bootloader, flash a partition, enable root, promote a device profile or satisfy a beta hardware gate.

## Threat model

A long-running self-hosted build can reference a valid-looking `adb` path while the file behind that path is replaced, redirected through a symlink or made broadly writable. Runtime reports collected with different tool bytes should not be treated as one coherent run.

`swirphoneos.runtime_tool_evidence` therefore fails closed unless the selected tool is:

- an absolute path that is already canonical;
- named exactly `adb`;
- a regular non-symlink file;
- executable by the builder account;
- non-empty and no larger than the bounded collector limit;
- not group- or world-writable.

The collector reads and hashes the file but deliberately never executes it. The absolute path is not emitted in the public JSON; a SHA-256 path identity is stored instead.

## Evidence window

When `collect_runtime=true`, `.github/workflows/aosp-build-evidence.yml` now uses this sequence:

1. builder preflight passes;
2. the selected canonical `adb` is captured to `runtime-tool-evidence.json` before source synchronization/build work proceeds;
3. the same file is re-hashed immediately before Cuttlefish launch and written to `runtime-tool-prelaunch-verification.json`;
4. runtime identity and all source-ready app smoke checks use the selected `SWIR_ADB_PATH`;
5. the file is re-hashed again after app smoke and written to `runtime-tool-post-verification.json`;
6. the normal build/runtime chain is bound to those exact tool reports as `runtime-trust-bundle.json`.

A changed path identity, size, SHA-256, unsafe permission state, malformed evidence, duplicate JSON key or forged write/promotion flag rejects the trust chain.

## Runtime trust bundle

`python -m swirphoneos.runtime_trust_bundle` accepts only a completed `BUILD_AND_RUNTIME` AOSP run plus matching capture/pre-launch/post-run adb evidence. The resulting report binds:

- the canonical AOSP run evidence digest;
- the exact built fingerprint digest;
- the exact adb SHA-256, bounded size and path-identity SHA-256;
- SHA-256 values for every JSON input file;
- proof that the selected adb bytes were unchanged across the measured runtime window.

The bundle keeps `device_write_allowed=false`, `physical_device_support_claimed=false` and `status_promotion_performed=false`.

## Workflow input hardening

Dispatch values are mapped to job environment variables before shell execution. Job-count and runtime-mode values are validated before use, and the adb path is consumed only as a quoted environment variable. Direct `${{ inputs.* }}` interpolation into `repo sync`, `m`, runtime adb arguments and shell path checks is rejected by source tests.

## What this does not prove

Even a complete runtime trust bundle does **not** prove:

- that a SwirPhoneOS AOSP build has succeeded unless the underlying build evidence is complete;
- physical phone compatibility;
- telephony, camera, audio or sensor behavior on real hardware;
- install, rollback or stock restore safety;
- accessibility, visual quality or all locale/RTL behavior;
- SwirRoot support;
- beta readiness.

Those remain separate evidence gates. The current project percentage and beta gate must not increase from runtime-tool trust plumbing alone.
