<p align="center"><img src="branding/swirphoneos.svg" width="112" alt="SwirPhoneOS icon"></p>
<h1 align="center">SwirPhoneOS</h1>
<p align="center">An Android-compatible mobile OS and a safety-first PC companion. By Swir.</p>

> **Foundation 0.0.1-dev. No bootable OS image, Windows installer or supported phone is available yet.**

![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Progress](https://img.shields.io/badge/roadmap-2%25-168BFF)
![Beta](https://img.shields.io/badge/beta-BLOCKED-orange)

## Overall progress

<!-- PROJECT-PROGRESS:START -->
**2 / 100 weighted milestone points = 2%**

`[....................] 2%`
<!-- PROJECT-PROGRESS:END -->

The 20-cell bar uses one filled cell per complete 5 percentage points. Foundation earns 2 points; OS boot and hardware validation earn none until actually tested. See [ROADMAP.md](ROADMAP.md) and [progress.json](progress.json).

## What exists today

A dependency-free Python offline preflight prototype, a strictly PLANNED AC2003/avicii profile, synthetic fixtures, host tests, project documentation and a custom SVG application icon. The prototype reads local JSON and produces a sanitized assessment. It does **not** connect to phones, run ADB/Fastboot, build Android, unlock, flash, erase, back up or restore anything. Android properties are untrusted hints, not proof of physical identity or unlock state. All write operations remain blocked.

## Intended product

A maintainable AOSP/Linux-based Android-compatible system, modular Swir launcher/SystemUI/settings, ARM64 GSI where vendor compatibility permits, and device-specific support where required. SwirPhoneOS Flash Studio is the planned Windows/Linux companion for diagnostics, verified installation, recovery and updates. This project is separate from KaliPhoneStudio, Konofix and SWIR OS Desktop.

The first **planned** reference target is OnePlus Nord AC2003 (`avicii`). GSI does not guarantee compatibility with every Android phone. See [Architecture](ARCHITECTURE.md) and the upstream sources there. Do not flash the synthetic example or treat the profile as hardware support.

## Run the host prototype

From the repository root, with Python 3.11 or newer (CI targets 3.11-3.14; consult the actual CI result):

```sh
python -m unittest discover -s tests -v
python -m swirphoneos --profile device_packs/oneplus/avicii/profile.json --snapshot examples/avicii-properties.SYNTHETIC.json
```

Preflight exit **2 means BLOCKED**, as intended. Exit 1 means invalid/unreadable input. The example contains synthetic property hints, not measurements from a connected phone. No dependencies, administrator rights or USB connection are required.

## Beta release policy

A real GitHub beta prerelease is authorized only after [BETA_RELEASE_GATE.md](BETA_RELEASE_GATE.md) passes for the exact candidate build. Source archives, GUI mockups and host tests are not a mobile OS beta. Physical phone tests require the owner's participation and cannot be manufactured by unattended development.

## Development standards

Repository-facing content is English. Future graphical interfaces must select the system language on first launch, fall back to English, support extensible translations, preserve the custom app icon and show a `by Swir` footer linking to GitHub. The current CLI is English-only. No paid infrastructure is provisioned automatically. See [AGENTS.md](AGENTS.md), [BUILD_STATUS.md](BUILD_STATUS.md) and [SECURITY.md](SECURITY.md).

---
**by Swir** · [GitHub](https://github.com/Swir)
