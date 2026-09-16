# SwirRoot engineering contract

SwirRoot is the first-party root manager planned for explicitly supported SwirPhoneOS builds. The repository now contains a meaningful **Android source-stage** SwirRoot application in addition to the host policy validator: an original localized owner UI, a non-exported status/diagnostic service, a bounded app-private review audit and a pure-Java transition policy.

It is still **not a working root implementation**. The checked-in Android service hard-disables the mutation backend and supported-build switch, reports `UNAVAILABLE`, and contains no boot-image patcher, bootloader unlocker, process-execution path, partition writer or exploit/bypass mechanism. The UI can review enable/unroot prerequisites after explicit owner confirmation, but it cannot execute those transitions.

## Current Android source-stage behavior

The `SwirRoot` AOSP module is included in the developer Cuttlefish product as `ANDROID_SOURCE`. It currently provides:

- visible `UNAVAILABLE` / ROOT OFF / ROOT ON / TRANSITION state vocabulary;
- the current Android build fingerprint for diagnostics;
- explicit owner-confirmed review dialogs for enable-root and unroot planning;
- a non-exported bound service, inaccessible as a public IPC surface;
- a bounded app-private audit of workflow reviews and denial reasons;
- a host-tested pure-Java safety policy for the future transition backend;
- EN/PL/NB/DE/ES/FR/PT/AR resources and locale-driven RTL layout.

The review audit is **not** the future durable mutation transaction journal. It records only UI/diagnostic review events and therefore cannot satisfy the `journal_available` gate for an actual root transition.

The registry currently treats `root_state` and `authorization_audit` as source-implemented capabilities. `guided_enable` and `guided_unroot` remain unimplemented target capabilities until an exact build/profile has a legitimate tested backend and rollback path.

## State model

SwirRoot uses four explicit states:

- `UNAVAILABLE` — the current build/profile is not approved for root operations;
- `ROOT_OFF` — a supported build is in its verified non-root state;
- `ROOT_ON` — a supported build is in its verified rooted state;
- `TRANSITION` — a state-changing operation is in progress and must be journaled/recoverable.

Unverified builds default to `UNAVAILABLE`, not `ROOT_OFF`, because claiming root is safely disabled would itself require exact-build evidence. The current Android service therefore always reports `UNAVAILABLE`.

## Enable-root gate

A future implementation may offer an executable enable action only after all of these are true for the exact build/profile:

- exact build match;
- verified device profile;
- explicit owner confirmation;
- verified rollback material;
- durable operation journal availability;
- update state is safe for the transition;
- the exact build is explicitly supported by the mutation backend.

Passing the pure-Java policy returns only an eligible `TRANSITION` plan. The current source has no executor and cannot make the device rooted.

## Unroot gate

The unroot path must know and verify the expected non-root state, require owner confirmation, retain rollback material and use the same durable transaction journal. Unroot is considered implemented only after exact-build physical validation demonstrates enable → reboot → use → disable → reboot/recovery behavior and verifies that the expected non-root boot/system state was restored.

## Authorization model

Future per-app root grants are deny-by-default, individually revocable and auditable. An emergency global disable path is mandatory. Root enablement must never silently grant unrestricted background root to every installed package.

The current source-stage audit is not a privileged authorization broker; it only records owner workflow reviews. A real privileged authorization backend remains future work.

## Forbidden methods

The policy rejects any design that depends on bootloader exploits, OEM/vendor-protection bypasses, silent unlock, unattended flash operations or account-lock bypass. SwirRoot is for owner-controlled supported builds and legitimate boot/image modification paths only, not security-control circumvention.

The Android source validator also scans all production Java files and rejects process-execution/network/storage primitives that are outside the reviewed source-stage contract. SwirRoot receives extra checks that mutation support remains hard-disabled and that no reviewed device-write primitives are introduced accidentally.

## Machine-readable and Android contracts

`swirroot/policy.json` remains the host-side authoritative safety contract and is validated by `swirphoneos/swirroot.py` and CI:

```sh
python -m swirphoneos root-policy
python -m swirphoneos android-apps
```

At the current development stage host policy `write_operations_enabled` is `false`, its `supported_builds` list is empty, Android `WRITE_BACKEND_ENABLED` is `false`, Android `SUPPORTED_BUILD` is `false`, and root availability is therefore false. The pure-Java `RootPolicyHostTest` exercises the decision gates without performing any Android or device write.

## Required path to real root support

Before SwirRoot can execute anything, the project must have a real bootable SwirPhoneOS build, a verified physical device/profile, a legitimate owner-supported boot path, verified backup/rollback material, a durable recovery journal, a known non-root restore state and tested recovery. Only then can an exact build identifier be allowlisted and a build-specific mutation backend be implemented and reviewed.

SwirRoot state must integrate with Swir Update, recovery and SwirPhoneStudio so OTA, restore and root transitions cannot silently invalidate each other. Physical enable/unroot/recovery evidence is required before any beta root claim.
