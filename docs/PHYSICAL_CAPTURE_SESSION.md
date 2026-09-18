# Read-only physical-device capture sessions

SwirPhoneOS provides a create-only capture workflow for collecting the existing strict ADB and Fastboot/FastbootD diagnostic evidence from one owner-controlled phone across a manual transport-mode transition.

This workflow is preparation evidence only. It **does not** reboot the phone, unlock the bootloader, erase data, flash a partition, install SwirPhoneOS, enable root, restore stock firmware, promote a device profile, or mark a beta gate complete.

## Why this exists

The repository already has two independent read-only diagnostic surfaces:

- `ReadOnlyAdb` records a bounded set of Android properties from exactly one local authorized USB phone.
- `ReadOnlyFastboot` records a bounded allowlist of Fastboot/FastbootD variables and, when requested, reviewed partition size/slot hints.

A real owner/operator normally has to transition the same phone manually between Android/ADB and Fastboot/FastbootD. The capture session makes that multi-step evidence collection reproducible without adding an automated reboot or any other device write.

Each session binds:

1. the exact raw SHA-256 of every reviewed `device_packs/*/*/profile.json` file at session creation;
2. one create-only ADB unified report with exact ADB executable SHA-256 and hashed USB transport serial;
3. one create-only Fastboot unified report with exact Fastboot executable SHA-256 and the same hashed USB transport serial;
4. the existing cross-transport `hardware_evidence` result;
5. a final canonical capture bundle that binds the exact persisted report-file bytes.

The raw USB serial is not stored by the capture workflow.

## Safety boundary

Every persisted session and final bundle hard-codes these outcomes:

- `hardware_verified = false`
- `support_claim_allowed = false`
- `profile_promotion_allowed = false`
- `install_allowed = false`
- `device_write_allowed = false`
- `root_allowed = false`

The current `oneplus/avicii` profile remains `PLANNED_NOT_SUPPORTED`. A matching capture is useful evidence for later human review, but it is not a verified partition map, stock-restore proof, install/rollback proof, SwirPhoneOS boot proof, or capability verification.

The command surface intentionally has no reboot, flash, erase, format, boot, unlock, relock, install, root, unroot, restore, set-active, OEM, or arbitrary shell command.

## Operator flow

Use trusted Android SDK Platform Tools and an absolute session directory on the local machine.

Create a new evidence session:

```bash
python -m swirphoneos.device_capture_session_cli create \
  --session-dir /absolute/path/to/avicii-capture
```

With the owner-controlled phone booted into Android, USB debugging explicitly authorized, and exactly one local USB phone connected:

```bash
python -m swirphoneos.device_capture_session_cli capture-adb \
  --session-dir /absolute/path/to/avicii-capture \
  --adb /absolute/path/to/adb
```

The tool stops after the read-only ADB observation. **Manually** place the same phone into the reviewed Fastboot/FastbootD mode using the phone's normal supported controls. The capture tool does not reboot the device.

Capture Fastboot evidence:

```bash
python -m swirphoneos.device_capture_session_cli capture-fastboot \
  --session-dir /absolute/path/to/avicii-capture \
  --fastboot /absolute/path/to/fastboot \
  --partitions
```

`--partitions` only enables the existing bounded `has-slot:<name>` and `partition-size:<name>` read-only getvar allowlist. It never runs `getvar all`.

Correlate the two saved observations:

```bash
python -m swirphoneos.device_capture_session_cli finalize \
  --session-dir /absolute/path/to/avicii-capture
```

Re-read all persisted evidence and verify the exact-byte bindings later:

```bash
python -m swirphoneos.device_capture_session_cli verify \
  --session-dir /absolute/path/to/avicii-capture
```

## Create-only evidence layout

A completed session contains:

```text
avicii-capture/
├── session.json
├── adb-report.json
├── fastboot-report.json
├── hardware-evidence.json
└── capture-bundle.json
```

Files are created with exclusive-create semantics. Existing evidence is not silently overwritten. The session also refuses to continue if the reviewed device-profile registry changes after `session.json` was created.

## What finalization checks

Finalization reuses the existing fail-closed hardware correlator. Among other checks, it requires:

- both reports to resolve to one unique local metadata profile hint;
- exact transport-tool provenance digests;
- the same hashed USB transport serial across ADB and Fastboot;
- model/codename compatibility with the snapshotted metadata profile;
- an exact ADB build fingerprint;
- no contradictory current-slot observation;
- no contradictory bootloader-state observation when both transports report one.

The result remains `CORRELATED_READ_ONLY_CAPTURE_COMPLETE_NOT_VERIFIED`.

## Relationship to later support evidence

This session should feed later evidence review, not replace it. Device-support readiness still requires independent physical evidence for:

- verified physical hardware identity;
- a verified partition map;
- verified stock restore;
- verified SwirPhoneOS boot;
- a full install cycle;
- a full rollback cycle;
- the core phone experience and exact-device capability matrix.

Only a separately reviewed future support-capable profile schema may promote a device from metadata-only planning status. The current capture workflow has no code path that can perform that promotion.

## Privacy

The exported JSON contains device-reported model/codename/build information and SHA-256 digests that may still be linkable across local evidence. Treat the capture directory as owner-controlled diagnostic material. Review it before sharing publicly.
