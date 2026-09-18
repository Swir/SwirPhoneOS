# Cuttlefish visual capture and review evidence

SwirPhoneOS keeps automated runtime launch/localization evidence separate from human visual review. The post-run visual evidence path captures bounded PNG screenshots from the exact retained Cuttlefish build only after a successful runtime-enabled `AOSP build evidence` run.

## What automated capture proves

When the workflow completes, the evidence binds one PNG to every source-ready package and checked-in locale pair. Each capture is taken only after the requested per-app locale is observed and the package-local launcher is confirmed as the foreground activity. The capture report records exact PNG size, SHA-256 and dimensions. A second trust bundle re-reads every PNG, rejects missing/extra/symlink entries, and binds the closed capture directory to the existing exact build/runtime/i18n/ADB trust chain.

The workflow also re-verifies retained `boot.img` / `system.img` build-artifact continuity before launch and verifies the exact trusted `adb` bytes before and after capture. Build-only AOSP runs have no runtime review bundle, so the visual path is a safe no-op for them.

Automated capture does **not** decide whether translations are correct, text is clipped, Arabic is mirrored correctly or accessibility is acceptable. Those claims remain false until separate review evidence exists.

## Human visual review template

A runtime-enabled successful post-run capture also emits `runtime-visual-review-template.json`. The template is deterministic and bound to the exact `runtime-visual-trust-bundle.json`, exact visual-capture digest and every individual screenshot SHA-256. It contains one review item for every package/locale pair.

The generated template intentionally starts with:

- `reviewer` empty;
- `reviewed_at_utc` empty;
- `translation = PENDING` for every capture;
- `text_clipping = PENDING` for every capture;
- `rtl_mirroring = PENDING` only for RTL captures and `NOT_APPLICABLE` for LTR captures.

The workflow never fills these values automatically. A reviewer must inspect the exact retained PNGs, enter a bounded reviewer label and UTC timestamp, and change each applicable check to `PASS` or `FAIL`. Failed observations should be explained in the bounded `note` field rather than being hidden by changing the evidence scope.

A completed review can be verified offline against the exact trusted evidence:

```sh
python -m swirphoneos.runtime_visual_review verify \
  --visual-trust /absolute/path/to/runtime-visual-trust-bundle.json \
  --visual-report /absolute/path/to/runtime-visual-evidence.json \
  --review /absolute/path/to/completed-runtime-visual-review.json \
  > runtime-visual-review-evidence.json
```

The verifier rejects duplicate JSON keys, unknown fields, PENDING final checks, cross-run/trust-digest drift, changed package/locale/capture identity, swapped screenshot hashes, LTR records that claim an RTL result and RTL records without an explicit mirroring result. It computes review-complete and pass/fail values from the per-capture checks instead of trusting reviewer-supplied summary booleans.

A completed visual review remains a human attestation. It can establish that the exact captured matrix was reviewed for translation, clipping and RTL mirroring, but it cannot establish TalkBack behavior, semantic labels, focus order, keyboard/input behavior, touch-target quality or other accessibility requirements. `accessibility_review_complete` therefore remains false in visual-review evidence.

## Safety boundary

This is Cuttlefish-only evidence. The accepted ADB transport must be local, and the collector exposes no arbitrary shell surface. It may change only per-app locale overrides and transient foreground activity state on the disposable guest. Every captured locale override is restored before evidence is accepted. PNG files are written create-only to a new host evidence directory.

The automated visual report and trust bundle deliberately keep all of these values false:

- `rtl_visual_mirroring_verified`
- `accessibility_review_complete`
- `visual_translation_review_complete`
- physical-device support/write claims
- application/status promotion
- release-artifact authorization

The human-review verifier may set `visual_translation_review_complete` and `rtl_visual_mirroring_verified` only from a fully completed exact-bound attestation. It always keeps accessibility, physical-device writes/support, application promotion and release authorization false.

The path performs no package install/uninstall, root, phone reboot, flash, erase, bootloader operation or physical-device command.

## Evidence outputs

A runtime-enabled successful post-run capture uploads an immutable artifact containing:

- `aosp-artifact-continuity.json`
- `visual-runtime-evidence.json`
- `visual-adb-pre-verification.json`
- `visual-adb-post-verification.json`
- `runtime-visual-evidence.json`
- `runtime-visual-trust-bundle.json`
- `runtime-visual-review-template.json`
- the closed `runtime-visual/*.png` package/locale matrix

A completed `runtime-visual-review-evidence.json` is intentionally a later reviewer-produced artifact and is not manufactured by the automated capture workflow.

This work does not change `project.json`. Weighted engineering progress remains governed only by completed milestone evidence, and source/host/visual-capture/review infrastructure cannot satisfy build, boot, accessibility or physical-device gates by itself.
