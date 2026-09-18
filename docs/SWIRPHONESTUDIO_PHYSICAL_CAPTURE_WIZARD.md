# SwirPhoneStudio physical-device capture wizard

SwirPhoneStudio now exposes the repository's create-only physical-device evidence session as an owner-visible desktop workflow in the frozen Windows package.

This is **not** an installer and it does not make a device supported. The wizard is deliberately limited to the existing read-only ADB and Fastboot/FastbootD inspection paths plus exact-byte evidence finalization and verification.

## Safety boundary

The wizard does not expose an automated reboot, boot command, bootloader unlock/relock, flash, erase, format, install, root, unroot, restore, set-active operation, OEM command, or arbitrary shell command. Mode changes remain manual and owner-controlled.

A completed capture still records:

- `hardware_verified = false`
- `support_claim_allowed = false`
- `profile_promotion_allowed = false`
- `install_allowed = false`
- `device_write_allowed = false`
- `root_allowed = false`

A matching `oneplus/avicii` observation therefore remains preparation evidence only; the profile stays `PLANNED_NOT_SUPPORTED` until the separate physical-support gates are actually satisfied.

## Desktop flow

The Windows entry point now launches a small desktop shell around the existing Studio UI. The **Tools → Physical device capture** action opens the capture wizard without changing the existing diagnostic surfaces.

The owner flow is:

1. Choose a new absolute session path and create the create-only session descriptor.
2. Select a trusted `adb` executable and capture the strict read-only ADB observation.
3. Manually place the same owner-controlled phone into the reviewed Fastboot/FastbootD mode using its normal supported controls.
4. Select a trusted `fastboot` executable and capture the strict read-only Fastboot observation. The optional partition checkbox only enables the existing bounded size/slot hints.
5. Finalize the session to correlate the two persisted observations through the existing hardware-evidence policy.
6. Verify later to re-read every persisted evidence byte and rebuild the correlation.

Each step runs off the Tk event loop so the desktop UI remains responsive. Errors are mapped to a localized generic message; raw subprocess output, private file paths, and device identifiers are not displayed by the wizard.

## Localization

The capture surface is supplied through the shared data-only localization architecture. It currently ships complete strings for the same host-tool locale set:

- English (`en`) — canonical source/fallback
- Polish (`pl`)
- Norwegian Bokmål (`nb`)
- German (`de`)
- Spanish (`es`)
- French (`fr`)
- Portuguese (`pt`)
- Arabic (`ar`)

The Tools menu and an already-open wizard follow the shared Studio language selection.

## Frozen package behavior

`packaging/studio_entry.py` launches `swirphoneos.studio_desktop.main`. PyInstaller already bundles `device_packs` and the complete `swirphoneos/locales/catalogs.d` directory, so the frozen executable uses the exact packaged profile registry and capture translations. The helper resolves the profile root from PyInstaller's runtime bundle when frozen and from the repository root during source development.

The existing `--smoke-test` contract is preserved and does not touch Android SDK tools or a phone.

## Verification scope

Host tests cover workflow ordering, relative-path rejection, private-error suppression, reuse of the strict ADB/Fastboot inspectors, explicit partition-hint opt-in, frozen registry resolution, full locale coverage, Windows entry-point integration, and absence of known device-write command strings from the wizard module.

Those tests verify source behavior only. They do not satisfy physical hardware verification, Windows USB runtime verification, install/rollback, SwirPhoneOS boot, or any beta gate.
