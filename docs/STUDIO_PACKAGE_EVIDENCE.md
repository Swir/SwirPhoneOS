# SwirPhoneStudio package provenance evidence

SwirPhoneStudio is currently a **developer package**, not a release installer and not proof that a physical phone can be safely installed, restored or rooted from Windows.

The Windows packaging workflow now produces three files together:

- `SwirPhoneStudio.exe`
- `SHA256SUMS.txt`
- `SwirPhoneStudio-evidence.json`

The evidence report is generated only after the one-file executable has built, the frozen GUI smoke test has passed and the executable SHA-256 has been recorded. The workflow then immediately revalidates the report against the exact executable and checksum bytes before uploading the artifact bundle.

## What the report binds

Schema v1 binds the package to:

- the exact 40-character Git source commit reported by GitHub Actions;
- repository `Swir/SwirPhoneOS`;
- reviewed workflow path `.github/workflows/package-studio.yml`;
- GitHub Actions run id and attempt;
- target `windows-x64`;
- exact `SwirPhoneStudio.exe` byte size and SHA-256;
- a verified Windows PE `MZ` header;
- exact `SHA256SUMS.txt` bytes and the executable digest recorded by that file;
- the pinned Python 3.14 packaging line;
- pinned PyInstaller `6.22.3`;
- a canonical SHA-256 over the complete evidence payload.

Input files must be regular non-symlink files with exact expected names and bounded sizes. The executable and checksum file must come from the same package directory. Evidence JSON is strict UTF-8, rejects duplicate keys and uses an exact field inventory.

## Fail-closed status boundaries

Package provenance deliberately keeps all of these values false:

- `windows_usb_runtime_verified`
- `release_artifact`
- `beta_gate_passed`
- `device_write_allowed`

It also keeps `developer_package_only=true`.

A successful frozen GUI smoke test proves only that the packaged application can start in the CI environment under the existing smoke contract. It does **not** prove owner-controlled Windows USB ADB/Fastboot/FastbootD behavior, exact-device diagnostics, flashing, recovery, SwirRoot operation or beta readiness.

## Local revalidation

The same module can revalidate a downloaded workflow artifact without executing the packaged program:

```powershell
python -m swirphoneos.studio_package_evidence verify `
  --report .\SwirPhoneStudio-evidence.json `
  --exe .\SwirPhoneStudio.exe `
  --checksums .\SHA256SUMS.txt
```

Revalidation checks the evidence digest and then hashes the exact executable and checksum file again. Any changed executable size/content, checksum content, package identity or unauthorized status promotion is rejected.

The workflow collector is intended for GitHub Actions and expects the standard `GITHUB_SHA`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` environment identity.

## What is still required for the desktop milestone

This evidence improves package provenance but does not complete `desktop_diagnostics` or the beta `windows_runtime` gate. The remaining high-value desktop proof is real owner-controlled Windows USB smoke against a known phone across the read-only ADB and Fastboot/FastbootD surfaces, with the resulting observations reviewed for correctness and privacy before any future write-capable design is considered.
