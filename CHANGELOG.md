# Changelog

## Unreleased

Added a strictly read-only Fastboot/FastbootD diagnostic path to the Python host tooling. It requires an explicit trusted Android SDK `fastboot` executable, exactly one local USB device and a small `getvar` allowlist (`product`, `current-slot`, `slot-count`, `unlocked`, `is-userspace`, `secure`). Mutating commands are rejected, device identity is rechecked, private serial values are not included in reports, and the result always keeps `flash_allowed` false. Added cross-platform mocked unit coverage and a CLI `inspect-fastboot` command.

Added a strict schema-v1 device profile registry and `profiles` CLI command. The validator enforces bounded safe IDs/model lists, HTTPS source metadata and duplicate-ID detection. Schema v1 is intentionally metadata-only: profiles with `flash_enabled: true` or executable flash operations are rejected. The existing OnePlus Nord AC2003 (`oneplus/avicii`) placeholder is now validated by the same registry without becoming a supported device.

Added the first **SwirPhoneStudio** desktop GUI source as a read-only developer preview. It exposes profile validation, ADB inspection and Fastboot/FastbootD inspection without any write controls; uses a dark desktop layout; detects Polish/Norwegian/English from the OS locale with English fallback; includes a `by Swir` GitHub footer; and supports sanitized JSON report export. The report exporter rejects sensitive identifier fields including serial/IMEI/MEID and applies bounded JSON validation before writing.

Added an offline Android 17 / API 37 AOSP baseline candidate record plus strict validation and a `baseline` CLI command. On the 2026-09-16 upstream check, `android-latest-release` resolved to `android17-release`; the candidate references `android-17.0.0_r1` / `CP2A.260605.016`. Status remains `CANDIDATE_NOT_PINNED`: no source sync or platform build is claimed. Added an upstream pinning/reproducibility policy and CI checks for both the device registry and baseline metadata.

Added unit coverage for locale mapping, translation fallback, privacy-checked report export and platform-baseline overclaim prevention. The GUI is lazily imported so headless status/gate CI remains independent of Tk availability.

This does not add supported phones, flashing, bootloader unlocking, image booting, restore capability, a packaged Windows EXE or beta readiness. Project progress remains 2% until evidence-backed roadmap gates actually complete.

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics with an explicit trusted-tool path, command allowlist, single-device selection, private errors, unknown-state handling and endpoint recheck. Added weighted progress accounting, strict mandatory beta-gate validation and a hard publication guard. Added 41 local host tests and a Windows/Linux Python 3.11–3.14 CI matrix with SHA-pinned Actions and read-only permissions. Added an original vector application icon, architecture, safety policy, development instructions and an explicitly unsupported avicii metadata profile.

No Android image, live-phone validation, GUI, Windows EXE or installation/restore capability is claimed for that baseline. Progress remains 2%; beta gates remain 0/9.

## 0.0.1 — Initial concept archive

The earlier SwirOS ZIP contained planning documentation. It was not a bootable OS, installer or hardware-supported release. Its scope is continued here with corrected safety and readiness distinctions.
