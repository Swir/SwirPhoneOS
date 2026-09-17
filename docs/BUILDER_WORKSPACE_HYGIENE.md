# Dedicated builder workspace hygiene

SwirPhoneOS evidence builds run on a persistent self-hosted Linux builder. A persistent workspace is useful for the large Android source checkout, but stale or locally injected state can make a build impossible to reproduce. The `build-preflight` command therefore performs a bounded, read-only workspace hygiene check before either the Cuttlefish or ARM64 GSI workflow starts `repo init` / `repo sync`.

## Fail-closed gates

A build-evidence run is rejected when any of the following is true:

- the selected workspace is not writable by the runner;
- the workspace resolves to `/` or to the runner account's home directory;
- `.repo/local_manifests/` contains any entry, including a symlink;
- legacy `.repo/local_manifest.xml` exists or is a symlink;
- `out/` contains any prior build state or is itself an alias/file instead of an empty directory;
- `vendor/swir` is a symlink.

These gates apply to the existing `build-preflight` command, so both manual evidence workflows inherit them without a separate opt-in. AOSP's resolved `repo manifest -r` evidence and the exact `vendor/swir` staging-tree closure remain separate later gates.

## Why local manifests are rejected

Repo local manifests can add, replace, or redirect source projects independently of the pinned upstream manifest. That flexibility is useful for normal Android development but is inappropriate for an evidence-producing SwirPhoneOS build unless the overlay is explicitly reviewed and represented in the repository. The dedicated evidence builder therefore rejects local-manifest state instead of silently synchronizing it.

This does not claim that every file in the Android checkout is clean. The resolved manifest, staging evidence, build identity and post-build source closure remain required. The workspace check only closes a high-impact persistent-runner injection path before synchronization begins.

## Why stale `out/` is rejected

The evidence path is intended to prove a fresh build result, not an incremental result that may reuse objects or images from a previous source revision. The preflight consequently requires an absent or empty `out/` tree.

The tool **never deletes** stale output. Cleanup is an operator action outside the evidence run and must be reviewed before retrying. This keeps the preflight read-only and prevents an automation error from recursively deleting an incorrectly configured path.

## Privacy and bounded reporting

The JSON report does not publish the absolute workspace path. It stores a SHA-256 of the canonical path as a local run identity and reports only bounded booleans plus free-space/inode metadata. It does not enumerate local-manifest filenames or Android source paths.

`cleanup_performed` is always `false`. A passing report is host/workspace readiness evidence only; it is not evidence that Android built, booted, passed Cuttlefish runtime checks, passed Treble/VTS, worked on physical hardware, or is safe to flash.

## Operator recovery

When the preflight rejects the workspace:

1. inspect the failed check ID in `builder-preflight.json`;
2. review the workspace manually and identify why the state exists;
3. remove or relocate only the specifically reviewed stale/local state outside the automation;
4. rerun the evidence workflow;
5. keep the resulting preflight, resolved manifest, staging report, build evidence and runtime evidence together.

Do not disable a gate just to make an evidence run pass. If a local manifest becomes a legitimate SwirPhoneOS dependency, represent that dependency explicitly in the checked-in platform/device build design and update the evidence contract in a reviewed change.

## Current project status

This hardening does not advance the weighted project milestone percentage. Until a real pinned Android 17 build completes, the exact SwirPhoneOS image boots, runtime evidence passes, and physical install/recovery gates are verified, project progress and Beta readiness remain unchanged.
