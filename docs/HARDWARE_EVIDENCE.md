# Read-only physical-device evidence

SwirPhoneOS treats device-reported ADB and Fastboot values as observations, not as trusted hardware identity or installation authorization. This workflow exists to collect better evidence for a future device-specific port while keeping all writes disabled.

## Safety boundary

The tooling in this document never unlocks, reboots, roots, erases, flashes, changes slots, formats partitions, installs packages or restores firmware. It accepts exactly one local USB device, rejects emulator/network transports and invokes only reviewed read-only commands.

ADB collection is limited to a fixed `getprop` allowlist. Fastboot collection is limited to a fixed `getvar` allowlist. Optional partition probing reads only `has-slot:<name>` and `partition-size:<name>` for a bounded reviewed set of partition names. `getvar all` is intentionally not used.

No raw USB serial number is written to generated reports. Each real transport capture instead stores the SHA-256 digest of the exact serial returned by that transport's enumeration command and the SHA-256 digest of the exact trusted `adb` or `fastboot` executable used for the capture. The tool binary is hashed before and after inspection; if its bytes change during the run, the capture fails closed. A serial digest is pseudonymous, stable data and should still be treated as share-sensitive. It is useful for correlation, not as a hardware identity credential.

## Capture an ADB observation

With Android booted normally and USB debugging explicitly authorized by the owner:

```sh
python -m swirphoneos inspect-device \
  --transport adb \
  --tool /absolute/path/to/adb \
  --profiles device_packs > adb-observation.json
```

The report records non-secret device/build hints including model, codename, ABI, board/hardware, Android release, security patch, exact build fingerprint, slot hints, bootloader/verified-boot state and dynamic-partition reporting. It also binds the observation to the SHA-256 of the enumerated transport serial and trusted ADB binary without retaining the raw serial. Device-reported values can be missing or spoofed and are not hardware verification.

## Capture a Fastboot observation

Move the phone to bootloader Fastboot or FastbootD **manually using the device's documented owner-controlled procedure**. SwirPhoneOS does not perform the transition.

```sh
python -m swirphoneos inspect-device \
  --transport fastboot \
  --tool /absolute/path/to/fastboot \
  --profiles device_packs \
  --partitions > fastboot-observation.json
```

The optional partition probe reads bounded size/slot hints for reviewed names such as `boot`, `vendor_boot`, `dtbo`, `vbmeta`, `super`, `system`, `product`, `vendor` and `userdata`. These hints are not a verified partition map and must never be converted directly into a flashing recipe. The report also records the SHA-256 of the Fastboot transport serial and exact trusted Fastboot executable used for the capture.

## Correlate the observations

```sh
python -m swirphoneos hardware-evidence \
  --adb-report adb-observation.json \
  --fastboot-report fastboot-observation.json \
  --profiles device_packs > hardware-evidence.json
```

The schema-v2 correlation is fail-closed. It requires both nested transport reports to pass their exact schema and provenance validation, requires both to point to one local metadata profile, requires the ADB model to match that profile's model allowlist, requires ADB and Fastboot codenames to agree with the profile, requires an exact ADB build fingerprint, requires valid SHA-256 provenance for both trusted SDK tools, requires the hashed transport serial to match across ADB and Fastboot, and rejects contradictory slot or bootloader-state reports when both transports provide them.

Some phones expose different identifiers in Android and Fastboot. Such a device deliberately fails this strict correlation path rather than being guessed equivalent. A future device-specific correlation mechanism may be introduced only after the identifier behavior is reviewed and tested for that exact profile.

The result includes a canonical SHA-256 over the evidence payload and always states:

- `hardware_verified=false`
- `swirphoneos_support=NOT_VALIDATED`
- `write_allowed=false`
- `flash_allowed=false`
- `root_allowed=false`

A matching transport-serial digest materially reduces accidental cross-device mixing, but it is **not cryptographic proof of physical hardware identity**: the identifier is device/tool reported and may be spoofed or cloned. Exact SDK-tool hashes improve capture provenance but do not make device-reported values trustworthy. A future hardware-verification milestone still requires controlled physical testing, known firmware provenance, a verified partition/restore map and successful rollback evidence on the exact device/build.

## Bind a transaction plan to the observed firmware

A local preparation-only transaction can be compared with the correlated evidence:

```sh
python -m swirphoneos transaction-device-check \
  --plan /absolute/path/to/plan.json \
  --hardware /absolute/path/to/hardware-evidence.json
```

A match requires the same profile, codename, model and exact current build fingerprint. Even a complete match produces only `PREPARATION_MATCH_ONLY`; it does not enable writes and does not satisfy physical hardware verification. The transport/tool provenance remains part of the integrity-hashed hardware evidence but does not relax rollback, owner-confirmation or physical-validation requirements.

## Current avicii status

`oneplus/avicii` remains `PLANNED_NOT_SUPPORTED`. This evidence path is intended to gather the inputs required to progress that profile safely. It does not change profile status automatically and it cannot enable SwirRoot or SwirPhoneStudio write controls.
