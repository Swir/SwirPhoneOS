# Changelog

## Unreleased

Added a strictly read-only Fastboot/FastbootD diagnostic path to the Python host tooling. It requires an explicit trusted Android SDK `fastboot` executable, exactly one local USB device and a small `getvar` allowlist (`product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace`, `secure`). Mutating commands are rejected, device identity is rechecked, private serial values are not included in reports, and the result always keeps `flash_allowed` false. Added cross-platform mocked unit coverage and a CLI `inspect-fastboot` command.

This does not add phone support, flashing, bootloader unlocking, image booting, restore capability or beta readiness. Project progress remains 2% until the full desktop-diagnostics gate has the required Windows/USB evidence.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics with an explicit trusted-tool path, command allowlist, single-device selection, private errors, unknown-state handling and endpoint recheck. Added weighted progress accounting, strict mandatory beta-gate validation and a hard publication guard. Added 41 local host tests and a Windows/Linux Python 3.11–3.14 CI matrix with SHA-pinned Actions and read-only permissions. Added an original vector application icon, architecture, safety policy, development instructions and an explicitly unsupported avicii metadata profile.

No Android image, live-phone validation, GUI, Windows EXE or installation/restore capability is claimed. Progress remains 2%; beta gates remain 0/9.

## 0.0.1 — Initial concept archive

The earlier SwirOS ZIP contained planning documentation. It was not a bootable OS, installer or hardware-supported release. Its scope is continued here with corrected safety and readiness distinctions.
