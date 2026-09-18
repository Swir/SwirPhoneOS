# Beta Release Gate

**BLOCKED — 0/9 mandatory gates passed. No release candidate or physical-device test evidence exists.**

A beta is a working SwirPhoneOS system plus a tested Windows installation companion, not a host-only preview, source ZIP or empty Release. Publication is authorized by the owner once these gates genuinely pass; it is part of the same development task.

| Required ID | Evidence required for the exact candidate |
| --- | --- |
| system_build | Pinned source manifest, completed bootable system build, image manifest and candidate commit |
| physical_boot | Physical AC2003 or explicitly approved reference model, exact firmware baseline, recorded boot into usable SwirPhoneOS |
| core_hardware | Display/touch, Wi-Fi/Bluetooth, scoped telephony/SMS/data, audio, storage, charging, thermal behavior and encryption; known limits recorded |
| install_restore | Real safe installation and tested recovery/stock-restore on that exact profile, with offline instructions |
| windows_runtime | Built Flash Studio Windows EXE; actual Windows launch and required installer workflow smoke tests |
| security_review | No known critical data-loss, thermal or security blocker; permissions, AVB/rollback and signing reviewed |
| artifact_trust | Actual permitted images/Windows package, SHA-256, trusted signatures and matching release manifest; no private keys or unauthorized vendor blobs |
| final_ci | Relevant checks green on the exact final candidate commit; pending, skipped or host-only checks cannot stand in for hardware evidence |
| release_docs | English release notes, supported model/firmware list, installation/recovery instructions, known issues and verified asset links |

## Evidence rules

Store sanitized test reports with candidate commit, build ID, device profile, firmware baseline, environment, test procedure, result and reviewer. Keep serials, IMEI, account identifiers and unlock credentials out of public evidence. Never convert mock results into physical-device evidence. Do not make test calls to public emergency numbers.

`project.json` is an accounting ledger, not proof by itself. The ledger validator checks mandatory IDs, types and evidence references and deliberately blocks publication even if every box is manually filled. The candidate-bundle verifier documented in [`docs/BETA_CANDIDATE_EVIDENCE.md`](docs/BETA_CANDIDATE_EVIDENCE.md) now adds a second fail-closed layer: for a future fully passed ledger it binds every referenced evidence file and required release artifact to exact local bytes, SHA-256, size, version and candidate commit while rejecting path traversal, symlinks, duplicate paths and duplicate JSON keys. That cryptographic binding is still not semantic proof that a file satisfies a gate. Gate-specific semantic evidence validators and real evidence remain mandatory, so candidate schema v1 always reports `beta_release_allowed=false`.

## Publishing procedure when ready

Review every gate; build from the exact recorded commit; verify checksums/signatures; create a versioned GitHub prerelease with actual tested permitted images and Windows package; verify tag/commit and uploaded assets; then report the release link and tested scope to the owner. Do not upload temporary private URLs or credentials. Do not duplicate an existing version.

A missing phone, matching firmware, build machine, signing setup or Windows smoke environment is a concrete blocker, not permission to invent success. Continue feasible engineering and report the missing evidence. No unattended unlock/erase/flash/relock of a physical phone is permitted.
