# SwirRoot engineering contract

SwirRoot is the first-party root manager planned for supported SwirPhoneOS builds. The current repository contains only a fail-closed policy contract and validator. It does **not** contain a working root service, boot-image patcher, bootloader unlocker or device-write path.

## State model

SwirRoot uses four explicit states:

- `UNAVAILABLE` — the current build/profile is not approved for root operations;
- `ROOT_OFF` — a supported build is in its verified non-root state;
- `ROOT_ON` — a supported build is in its verified rooted state;
- `TRANSITION` — a state-changing operation is in progress and must be journaled/recoverable.

Unverified builds default to `UNAVAILABLE`, not `ROOT_OFF`, because claiming root is safely disabled would itself require exact-build evidence.

## Enable-root gate

A future implementation may offer an enable action only after all of these are true for the exact build/profile:

- exact build match;
- verified device profile;
- explicit owner confirmation;
- verified rollback material;
- durable operation journal availability;
- update state is safe for the transition.

## Unroot gate

The unroot path must know and verify the expected non-root state, require owner confirmation, retain rollback material and use the same durable journal. Unroot is considered implemented only after exact-build physical validation demonstrates enable -> reboot -> use -> disable -> reboot/recovery behavior.

## Authorization model

Future per-app root grants are deny-by-default, individually revocable and auditable. An emergency global disable path is mandatory. Root enablement must never silently grant unrestricted background root to every installed package.

## Forbidden methods

The policy rejects any design that depends on bootloader exploits, OEM/vendor-protection bypasses, silent unlock, unattended flash operations or account-lock bypass. SwirRoot is for owner-controlled supported builds, not security-control circumvention.

## Current machine-readable contract

`swirroot/policy.json` is validated by `swirphoneos/swirroot.py` and CI:

```sh
python -m swirphoneos root-policy
```

At the current development stage `write_operations_enabled` is `false`, `supported_builds` is empty and `root_available` is therefore false. This is intentional. Enabling writes requires a later Android implementation, exact supported builds and physical rollback evidence; the host-side contract alone never authorizes a device modification.

SwirRoot state must eventually integrate with Swir Update, recovery and SwirPhoneStudio so OTA, restore and root transitions cannot silently invalidate each other.
