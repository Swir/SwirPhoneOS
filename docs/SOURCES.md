# Primary Upstream Sources

Checked 2026-09-16. Re-check before implementing platform or device operations. These references are not a SwirPhoneOS hardware-support certificate.

- AOSP latest-release/site updates: https://source.android.com/docs/whatsnew/site-updates — `android-latest-release` is the recommended current release manifest and resolved to `android17-release` on the checked date. A moving manifest is discovery input, not a reproducible SwirPhoneOS pin.
- AOSP build numbers/tags: https://source.android.com/docs/setup/reference/build-numbers — Android 17 is API 37; `android-17.0.0_r1` / `CP2A.260605.016` are recorded as the current SwirPhoneOS baseline candidate metadata.
- AOSP manifest repository: https://android.googlesource.com/platform/manifest — official Repo manifest source; exact revisions still need a preserved resolved manifest snapshot before the baseline is called pinned.
- AOSP Generic System Images: https://source.android.com/docs/core/tests/vts/gsi — Treble, unlock and platform testing requirements; a generic GSI is not universal device support.
- Android developer GSI overview: https://developer.android.com/topic/generic-system-image — purpose and scope of GSI testing.
- Bootloader locking/unlocking: https://source.android.com/docs/core/architecture/bootloader/locking_unlocking — device-owner confirmation and factory reset implications.
- Fastboot setup/flash guidance: https://source.android.com/docs/setup/test/running — unlocking deletes user data; commands differ by device. Do not copy examples into a universal installer.
- AOSP build environment: https://source.android.com/docs/setup/start/requirements — Linux x86-64 development guidance, at least 400 GB free space and minimum 64 GB RAM in the checked guidance. Re-check immediately before allocating a build host; no source sync or AOSP build was performed here.
- AOSP release signing: https://source.android.com/docs/core/ota/sign_builds — public test keys are not appropriate for public deployment.
- AOSP Vendor Test Suite: https://source.android.com/docs/core/tests/vts — kernel/HAL verification scope.
- avicii research entry: https://wiki.lineageos.org/devices/avicii/ — investigate exact variants and firmware; do not assume another ROM's support proves SwirPhoneOS support.

## CI source pins

Resolved through GitHub's tag API on 2026-09-16:

- actions/checkout v7.0.1: `3d3c42e5aac5ba805825da76410c181273ba90b1`
- actions/setup-python v7.0.0: `5fda3b95a4ea91299a34e894583c3862153e4b97`

These pins identify the Actions source; Python patch versions and hosted runner images remain CI-managed. The workflow is not a reproducible Android build.
