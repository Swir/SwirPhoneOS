# SwirPhoneOS Roadmap

![CI](https://github.com/Swir/SwirPhoneOS/actions/workflows/ci.yml/badge.svg)
![Progress](https://img.shields.io/badge/roadmap-2%25-168BFF)
![Beta](https://img.shields.io/badge/beta-BLOCKED-orange)

## Overall progress

<!-- PROJECT-PROGRESS:START -->
**2 / 100 weighted milestone points = 2%**

`[....................] 2%`
<!-- PROJECT-PROGRESS:END -->

This is a weighted engineering roadmap, not a count of commits or tests. Each milestone earns its full weight only after its defined outcome has been implemented and verified. The 20-cell bar rounds down to complete 5-point cells. Machine-readable source: [progress.json](progress.json).

| ID | Complete | Weight | Required verified outcome |
|---|---|---:|---|
| M00 | [x] | 2 | Repository foundation, honest scope, custom icon and tested offline preflight |
| M01 | [ ] | 10 | Pinned AOSP source/toolchain, license review and reproducible build setup |
| M02 | [ ] | 10 | Own system image boots in emulator with recorded runtime smoke test |
| M03 | [ ] | 12 | Usable Swir launcher/SystemUI/settings, accessibility and language selection |
| M04 | [ ] | 12 | ARM64 GSI build and documented vendor/Treble compatibility validation |
| M05 | [ ] | 20 | Physical reference-device boot and core hardware/telephony/media validation |
| M06 | [ ] | 10 | Encryption/privacy, charging, thermal, battery and suspend validation |
| M07 | [ ] | 10 | Windows/Linux companion with tested installation and stock recovery |
| M08 | [ ] | 8 | Signed OTA with device-tested update failure/recovery handling |
| M09 | [ ] | 6 | Exact-build beta gate, actual release artifacts and verified distribution |

**Completed: 1 of 10 milestones. Earned: 2 of 100 weighted points.**

M00 host test evidence: `tests/test_preflight.py`, synthetic fixture and BUILD_STATUS.md. Passing more host tests alone cannot complete M02-M09.

## Next engineering steps

Select and verify a current upstream baseline compatible with the target strategy; pin actual manifest revisions rather than a moving alias. Add build-host preflight and source-lock tooling, then obtain a bootable emulator image. Extend the desktop tool with non-destructive live diagnostics before planning writes. Add exact firmware and recovery evidence before approving any real device profile.

## Release sequence

Developer Preview: actual emulator build. Alpha: physical-device bring-up with recovery evidence. Beta: all mandatory exact-build gates passed. Stable: broader reliability/security/update validation. Additional devices and ecosystem features follow measured results, not unsupported universal-compatibility claims.
