# AOSP host and toolchain continuity evidence

SwirPhoneOS now has a fail-closed, read-only evidence layer for proving that one completed AOSP run used the same required host-tool bytes and the same static build-host identity across the build window.

This is reproducibility and provenance infrastructure. It does **not** build Android by itself and it does not grant weighted project credit, Android runtime status, physical-device support, install permission, SwirRoot support, or beta readiness.

## Trust boundary

`swirphoneos.aosp_host_evidence` records only bounded local facts. It never executes the discovered tools, installs packages, downloads source, changes the workspace, starts a build, launches Cuttlefish, reboots a phone, flashes a partition, or performs root operations.

For every command required by `build_preflight.REQUIRED_COMMANDS`, it resolves the executable, verifies that it is executable and a bounded regular file, hashes its exact bytes with SHA-256, and stores only a SHA-256 identity for its resolved path. Raw executable paths are not written to evidence.

The report also binds:

- the canonical AOSP workspace identity as SHA-256 rather than a raw host path;
- OS/machine/glibc identity;
- SHA-256 identities for the kernel release and `/etc/os-release` bytes when available;
- the complete required-tool inventory and one deterministic aggregate toolchain digest;
- KVM availability;
- RAM, free-space and inode counters as diagnostics only.

Resource counters are expected to change during a build, so they are deliberately excluded from `environment_identity_sha256`.

## Capture one build window

Use absolute paths and preserve all three JSON files as immutable build evidence:

```bash
PYTHONPATH="$GITHUB_WORKSPACE/tools" python -m swirphoneos.aosp_host_evidence \
  --workspace "$SWIR_AOSP_WORKSPACE" \
  --phase PRE_BUILD \
  > "$GITHUB_WORKSPACE/aosp-host-pre.json"

# Run only the already-reviewed pinned sync/stage/build/evidence pipeline here.

PYTHONPATH="$GITHUB_WORKSPACE/tools" python -m swirphoneos.aosp_host_evidence \
  --workspace "$SWIR_AOSP_WORKSPACE" \
  --phase POST_BUILD \
  > "$GITHUB_WORKSPACE/aosp-host-post.json"

PYTHONPATH="$GITHUB_WORKSPACE/tools" python -m swirphoneos.aosp_host_trust_bundle \
  --run-evidence "$GITHUB_WORKSPACE/aosp-run-evidence.json" \
  --host-pre "$GITHUB_WORKSPACE/aosp-host-pre.json" \
  --host-post "$GITHUB_WORKSPACE/aosp-host-post.json" \
  > "$GITHUB_WORKSPACE/aosp-host-trust-bundle.json"
```

The trust binder accepts normal free-space/inode drift but rejects any change to the workspace identity, static host identity, required command set, exact command bytes, resolved command-path identity, KVM availability, canonical evidence digests, or no-write/no-promotion safety flags.

A `BUILD_AND_RUNTIME` run additionally requires KVM to remain available across the complete build window.

## Deliberate non-claims

A valid host-trust bundle means only that the named completed AOSP run is cryptographically bound to an unchanged required host/toolchain identity between the two captures. It does not prove:

- that the Android image boots unless the bound run separately contains trusted runtime evidence;
- interactive visual, RTL or accessibility quality;
- Treble/VTS compliance;
- telephony, camera, audio or other physical-device capabilities;
- safe installation, rollback or stock restoration;
- SwirRoot enable/unroot support;
- beta readiness.

The first real `swir-aosp-builder` run still needs a synchronized exact `android-17.0.0_r1` checkout, successful image build, build evidence, and—when runtime collection is requested—the existing Cuttlefish boot/app/locale evidence chain.
