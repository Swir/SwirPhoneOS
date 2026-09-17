# Read-only physical-device evidence

SwirPhoneOS treats device-reported ADB and Fastboot values as observations, not as trusted hardware identity or installation authorization. This workflow exists to collect better evidence for a future device-specific port while keeping all writes disabled.

## Safety boundary

The tooling in this document never unlocks, reboots, roots, erases, flashes, changes slots, formats partitions, installs packages or restores firmware. It accepts exactly one local USB device, rejects emulator/network transports and invokes only reviewed read-only commands.

ADB collection is limited to a fixed `getprop` allowlist. Fastboot collection is limited to a fixed `getvar` allowlist. Optional partition probing reads only `has-slot:<name>` and `partition-size:<name>` for a bounded reviewed set of partition names. `getvar all` is intentionally not used.

No USB serial number is written to the generated reports.

## Capture an ADB observation

With Android booted normally and USB debugging explicitly authorized by the owner:

```sh
python -m swirphoneos inspect-device \
  --transport adb \
  --tool /absolute/path/to/adb \
  --profiles device_packs > adb-observation.json
```

The report records non-secret device/build hints including model, codename, ABI, board/hardware, Android release, security patch, exact build fingerprint, slot hints, bootloader/verified-boot state and dynamic-partition reporting. These values can be missing or spoofed and are not hardware verification.

## Capture a Fastboot observation

Move the phone to bootloader Fastboot or FastbootD **manually using the device's documented owner-controlled procedure**. SwirPhoneOS does not perform the transition.

```sh
python -m swirphoneos inspect-device \
  --transport fastboot \
  --tool /absolute/path/to/fastboot \
  --profiles device_packs \
  --partitions > fastboot-observation.json
```

The optional partition probe reads bounded size/slot hints for reviewed names such as `boot`, `vendor_boot`, `dtbo`, `vbmeta`, `super`, `system`, `product`, `vendor` and `userdata`. These hints are not a verified partition map and must never be converted directly into a flashing recipe.

## Correlate the observations

```sh
python -m swirphoneos hardware-evidence \
  --adb-report adb-observation.json \
  --fastboot-report fastboot-observation.json \
  --profiles device_packs > hardware-evidence.json
```

The correlation is fail-closed. It requires both reports to point to one local metadata profile, requires the ADB model to match that profile's model allowlist, requires ADB and Fastboot codenames to agree with the profile, requires an exact ADB build fingerprint, and rejects contradictory slot or bootloader-state reports when both transports provide them.

The result includes a canonical SHA-256 over the evidence payload and always states:

- `hardware_verified=false`
- `swirphoneos_support=NOT_VALIDATED`
- `write_allowed=false`
- `flash_allowed=false`
- `root_allowed=false`

Cross-transport correlation is **not cryptographic proof that the two reports came from the same physical phone**. A future hardware-verification milestone still requires controlled physical testing, known firmware provenance, a verified partition/restore map and successful rollback evidence on the exact device/build.

## Bind a transaction plan to the observed firmware

A local preparation-only transaction can be compared with the correlated evidence:

```sh
python -m swirphoneos transaction-device-check \
  --plan /absolute/path/to/plan.json \
  --hardware /absolute/path/to/hardware-evidence.json
```

A match requires the same profile, codename, model and exact current build fingerprint. Even a complete match produces only `PREPARATION_MATCH_ONLY`; it does not enable writes and does not satisfy physical hardware verification.

## Current avicii status

`oneplus/avicii` remains `PLANNED_NOT_SUPPORTED`. This evidence path is intended to gather the inputs required to progress that profile safely. It does not change profile status automatically and it cannot enable SwirRoot or SwirPhoneStudio write controls.
