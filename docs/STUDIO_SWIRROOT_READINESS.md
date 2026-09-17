# SwirPhoneStudio — SwirRoot readiness review

SwirPhoneStudio can review a previously generated `swirphoneos_swirroot_readiness_projection` JSON file. This feature is intentionally local and read-only. It exists so the owner can understand which mandatory SwirRoot gates are still missing without turning a preparation report into authorization.

## What the review accepts

The file must be an absolute-path regular `.json` file, not a symlink, and must stay below the bounded evidence size. JSON duplicate keys are rejected. The full report is passed through `validate_swirroot_readiness()` before any field is shown.

The desktop UI exposes only a bounded summary:

- requested action (`enable` or `unroot`),
- exact profile id,
- exact target build identity,
- transaction id,
- missing mandatory policy gates,
- whether the policy backend is available,
- whether a root transition is ready,
- whether device writes are allowed.

Evidence hashes and nested hardware/journal payloads are deliberately not copied into the UI summary.

## Safety boundary

The current readiness schema is correlation/preparation evidence only. Its validator requires:

- `hardware_root_authorized=false`,
- `transition_ready=false`,
- `device_write_allowed=false`,
- `root_operation_executed=false`,
- `status_promotion_performed=false`.

SwirPhoneStudio does not reinterpret those values. Opening a readiness file performs no ADB, Fastboot, reboot, unlock, boot-image modification, flash, erase, root, unroot or recovery operation. The readiness review button is also disabled while a USB diagnostic scan is in progress.

A report with a modified integrity hash, forged transition/write flag, wrong schema, unsupported provenance, duplicate JSON keys or unsafe filesystem form is rejected without exposing raw exception details in the GUI.

## Localization

Readiness-review UI strings are supplied by the shared host localization runtime through a strict data-only fragment under `swirphoneos/locales/catalogs.d/`. The fragment must cover every registered host locale with the exact same string-key set. The current translated set is EN, PL, NB, DE, ES, FR, PT and AR. Placeholder parity is still checked by the shared catalog validator.

## Evidence flow

```text
read-only ADB + Fastboot observations
              ↓
      hardware-evidence.json
              +
verified local target + rollback artifacts
              ↓
     recovery-journal.json
              +
        SwirRoot policy
              ↓
 swirphoneos.root_readiness_cli
              ↓
 SwirRoot readiness projection JSON
              ↓
 SwirPhoneStudio local review only
```

This feature does not advance the project to supported root, physical hardware support, install/restore completion or beta readiness. A future write-capable SwirRoot backend requires a separate authoritative physical-device evidence type, an exact supported build/profile, explicit owner confirmation, proven update-state safety, tested rollback/recovery and an independently verified unroot path.
