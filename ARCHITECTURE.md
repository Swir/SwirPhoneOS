# Architecture and boundaries

## Mobile platform

Use AOSP and the Linux kernel rather than inventing a new kernel or claiming native compatibility with every manufacturer. Keep Swir UX customizations modular to reduce upstream merge cost. ARM64 GSI is a compatibility route, not a guarantee that all hardware works. Per-device packs must bind identity, firmware, partitions, image format and recovery requirements. An actual AOSP baseline and source lock are still pending; this repository does not yet contain an Android platform checkout.

AOSP documents that there is no single GSI flashing procedure for every device and lists Treble and unlock requirements: [Generic system images](https://source.android.com/docs/core/tests/vts/gsi). Any installation workflow must be specific to a validated device/build pair.

## Desktop companion

The present `swirphoneos` package is an offline read-only foundation for Flash Studio. It validates bounded JSON, rejects ambiguous inputs, compares property hints with a PLANNED device profile, and returns explicit blockers. Unknown values remain unknown. No transport, installer, backup, image download or recovery backend exists yet. Imported properties can be spoofed and never authorize writes. Raw snapshots remain local; reports omit arbitrary extra properties such as serial numbers.

Future layers: read-only ADB/Fastboot adapters, device registry, artifact/signature verification, partition/firmware checks, persistent transaction journal, explicit confirmation and a separately reviewed write executor. A downloaded device pack must never execute arbitrary shell code. Merely setting a JSON support flag must not authorize a phone operation.

## Recovery and data

Bootloader unlocking can erase user data; a universal full backup cannot be promised. Protected/encrypted partitions may not be accessible. Never automatically unlock, erase, flash, relock, disable Verified Boot or alter rollback protection. A stock-restore route must be tested on the exact device variant and firmware before it is advertised as working. Source: [AOSP bootloader lock/unlock](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking).

## Updates and distribution

Plan signed system artifacts, independently authenticated update metadata, checksums, build provenance and controlled release channels. A checksum alone does not authenticate a publisher. Google services, banking-app compatibility and DRM are not guaranteed by APK compatibility; proprietary packages require an appropriate distribution/licensing path. Do not bundle restricted vendor components by default.

## Verification levels

Keep these distinct: concept -> host prototype -> built system -> emulator boot -> physical boot -> hardware-validated build -> tested installation/recovery -> beta release. CI fixtures are not phone evidence. The current project is at host prototype only.
