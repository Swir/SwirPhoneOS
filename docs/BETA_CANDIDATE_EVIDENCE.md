# Beta Candidate Evidence Binding

SwirPhoneOS uses a fail-closed candidate-bundle verifier before any future beta publication. The verifier is intentionally narrower than a release decision: it proves that the exact files referenced by a fully passed `project.json` gate ledger are present under one trusted local bundle root, match their recorded byte sizes and SHA-256 digests, and belong to the same exact candidate commit and version.

It does **not** decide that a screenshot proves a boot, that a hardware report proves telephony, that a CI log is from the correct run, or that recovery evidence proves a successful stock restore. Those are semantic claims and require dedicated gate-specific validators. Until those validators are implemented and reviewed, `beta_release_allowed` remains `false` even when every candidate file is cryptographically bound.

## Security properties

The v1 verifier is strict and fail-closed:

- the candidate commit must be an exact lowercase 40-hex commit and must match the project ledger;
- the candidate version must match the project ledger;
- all nine mandatory beta gates must already be explicitly passed and contain evidence references;
- the set of manifest `gate_evidence` paths must match the ledger evidence references exactly, with no missing or unreferenced evidence;
- every evidence and release file is re-read from disk and checked against its exact size and SHA-256 digest;
- absolute paths, `..`, backslashes, symlinks, duplicate paths, duplicate JSON keys and unknown record fields are rejected;
- the bundle must include at least one `os_image`, `windows_package`, `release_manifest` and `checksums` artifact;
- successful byte binding never enables device writes, status promotion or beta publication.

This verifier works only on local files. It performs no network access, no USB/device access and no installation or flashing.

## Manifest schema v1

The manifest contains only exact file bindings. Example structure:

```json
{
  "schema_version": 1,
  "candidate_commit": "0123456789abcdef0123456789abcdef01234567",
  "version": "0.1.0-beta.1",
  "evidence": [
    {
      "path": "evidence/system-build.json",
      "sha256": "<64 lowercase hex characters>",
      "size": 1234,
      "kind": "gate_evidence"
    }
  ],
  "release_artifacts": [
    {
      "path": "release/system.img",
      "sha256": "<64 lowercase hex characters>",
      "size": 123456789,
      "kind": "os_image"
    }
  ]
}
```

The full release artifact set must also contain `windows_package`, `release_manifest` and `checksums`. Optional reviewed kinds are `recovery_image`, `install_bundle` and `source_manifest`.

## Verification command

Run against an absolute trusted bundle root:

```bash
python -m swirphoneos.beta_candidate_cli \
  --ledger project.json \
  --manifest /absolute/path/to/candidate/candidate-manifest.json \
  --root /absolute/path/to/candidate
```

Exit code `1` means the bundle or ledger failed validation. Exit code `2` means exact file binding succeeded but beta publication is still blocked by the semantic evidence gate. There is intentionally no success code for publication in schema v1.

## What still blocks a beta

The real beta gate remains defined by `BETA_RELEASE_GATE.md`. SwirPhoneOS still needs, for one exact candidate, a reproducible bootable OS build, physical-device boot and core-hardware evidence, verified install and stock restore, Windows runtime evidence, security review, artifact trust, final CI and release documentation. The current project ledger remains at its truthful state until those facts exist.
