# AOSP source-tool trust

SwirPhoneOS treats the host commands used to synchronize Android source as part of the evidence boundary. The `swirphoneos.aosp_source_tool_evidence` module records the exact PATH-selected `repo` and `git` executable identities without executing either tool.

The capture is read-only. It records hashed lookup/canonical path identities, file size, SHA-256, executable state, alias state, and the exact two-tool set digest. Canonical targets must be regular executable files, must not be group/world writable, and are hashed with file-identity continuity checks so a file changed while it is being read is rejected.

A later verification repeats PATH resolution and byte hashing and requires exact equality with the captured evidence. `swirphoneos.aosp_source_tool_trust_bundle` can then bind a completed `BUILD_ONLY` or `BUILD_AND_RUNTIME` AOSP run to the unchanged `repo`/`git` evidence observed after source synchronization and after the build.

Example capture and verification on the dedicated Linux builder:

```sh
python -m swirphoneos.aosp_source_tool_evidence capture > /tmp/aosp-source-tools.json
# repo init/sync/manifest happens in the reviewed AOSP workflow
python -m swirphoneos.aosp_source_tool_evidence verify \
  --evidence /tmp/aosp-source-tools.json > /tmp/aosp-source-tools-postsync.json
```

After a completed build evidence chain, the trust binder accepts the run evidence plus the capture and two re-verifications:

```sh
python -m swirphoneos.aosp_source_tool_trust_bundle \
  --run-evidence /tmp/aosp-run-evidence.json \
  --tool-evidence /tmp/aosp-source-tools.json \
  --post-sync /tmp/aosp-source-tools-postsync.json \
  --post-build /tmp/aosp-source-tools-postbuild.json \
  > /tmp/aosp-source-tool-trust-bundle.json
```

## Security boundary

This evidence does **not** prove a successful source sync, Android build, Cuttlefish boot, physical-device compatibility, or beta readiness. It does not run `repo` or `git`, write to a phone, flash partitions, unlock a bootloader, enable root, publish a release, or promote project status. It only provides fail-closed byte continuity for the source-sync executables used by a separately verified AOSP run.

The current project completion percentage and beta gates must not change solely because this evidence tooling exists. Real build, boot, recovery, and physical-device evidence remain mandatory.
