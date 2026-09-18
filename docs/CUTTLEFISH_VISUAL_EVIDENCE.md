# Cuttlefish visual capture evidence

SwirPhoneOS keeps automated runtime launch/localization evidence separate from human visual review. The post-run visual evidence path captures bounded PNG screenshots from the exact retained Cuttlefish build only after a successful runtime-enabled `AOSP build evidence` run.

## What this proves

When the workflow completes, the evidence binds one PNG to every source-ready package and checked-in locale pair. Each capture is taken only after the requested per-app locale is observed and the package-local launcher is confirmed as the foreground activity. The capture report records exact PNG size, SHA-256 and dimensions. A second trust bundle re-reads every PNG, rejects missing/extra/symlink entries, and binds the closed capture directory to the existing exact build/runtime/i18n/ADB trust chain.

The workflow also re-verifies retained `boot.img` / `system.img` build-artifact continuity before launch and verifies the exact trusted `adb` bytes before and after capture. Build-only AOSP runs have no runtime review bundle, so the visual path is a safe no-op for them.

## Safety boundary

This is Cuttlefish-only evidence. The accepted ADB transport must be local, and the collector exposes no arbitrary shell surface. It may change only per-app locale overrides and transient foreground activity state on the disposable guest. Every captured locale override is restored before evidence is accepted. PNG files are written create-only to a new host evidence directory.

The visual report and trust bundle deliberately keep all of these values false:

- `rtl_visual_mirroring_verified`
- `accessibility_review_complete`
- `visual_translation_review_complete`
- physical-device support/write claims
- application/status promotion
- release-artifact authorization

Screenshots are inputs for focused human review; image existence is not proof that text is correct, unclipped, accessible or properly mirrored. The path performs no package install/uninstall, root, phone reboot, flash, erase, bootloader operation or physical-device command.

## Evidence outputs

A runtime-enabled successful post-run capture uploads an immutable artifact containing:

- `aosp-artifact-continuity.json`
- `visual-runtime-evidence.json`
- `visual-adb-pre-verification.json`
- `visual-adb-post-verification.json`
- `runtime-visual-evidence.json`
- `runtime-visual-trust-bundle.json`
- the closed `runtime-visual/*.png` package/locale matrix

This work does not change `project.json`. Weighted engineering progress remains governed only by completed milestone evidence, and source/host/visual-capture infrastructure cannot satisfy build, boot or physical-device gates by itself.
