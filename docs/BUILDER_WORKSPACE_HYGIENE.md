# Dedicated builder preflight and workspace hygiene

SwirPhoneOS evidence builds run on a persistent self-hosted Linux builder. A persistent workspace is useful for the large Android source checkout, but missing host prerequisites, an obsolete Repo launcher, stale output or locally injected source state can waste a many-hour build or make its result impossible to reproduce. The `build-preflight` command therefore performs a bounded, read-only host and workspace check before either the Cuttlefish or ARM64 GSI workflow starts `repo init` / `repo sync`.

The preflight does not execute Repo or any other external command. It performs local metadata inspection, command discovery and bounded static parsing of the installed Repo launcher bytes only. It never installs packages, downloads source, changes host configuration or cleans the workspace.

## Host gates before source synchronization

The current evidence path follows the official AOSP workstation requirements used by this repository:

- 64-bit Linux on x86-64;
- glibc 2.17 or later;
- at least 400 GiB of free space in the selected workspace filesystem;
- at least 64 GiB of RAM for a full evidence build;
- an installed Repo launcher whose static `VERSION` tuple is readable and is at least 2.4;
- the observable command counterparts for the current AOSP Ubuntu package guidance: `git`, `gpg`, `flex`, `bison`, `gcc`, `g++`, `zip`, `curl`, `xmllint`, `xsltproc`, `unzip` and `fc-list`;
- `bash`, `python3` and `repo`, which are also required by the checked-in evidence workflow.

`make` is reported as advisory because current AOSP release trees provide their own prebuilt Make, while the official Ubuntu package set still installs build-essential. The command checks intentionally do not pretend to prove development headers or libraries such as zlib/X11/OpenGL packages; those remain an operator responsibility and a real build can still expose a missing host dependency.

Repo version checking is deliberately non-executing. The preflight resolves the installed launcher as a regular file, bounds it to 1 MiB, and parses the launcher's `VERSION = (...)` tuple. A missing, unreadable, oversized or unparsable launcher is fail-closed. No command output, absolute executable path or network request is needed to establish the minimum 2.4 launcher gate.

## Workspace fail-closed gates

A build-evidence run is rejected when any of the following is true:

- the selected workspace is not writable by the runner;
- the workspace resolves to `/` or to the runner account's home directory;
- `.repo/local_manifests/` contains any entry, including a symlink;
- legacy `.repo/local_manifest.xml` exists or is a symlink;
- `out/` contains any prior build state or is itself an alias/file instead of an empty directory;
- `vendor/swir` is a symlink.

These gates apply to the existing `build-preflight` command, so both manual evidence workflows inherit them without a separate opt-in. AOSP's resolved `repo manifest -r` evidence and the exact `vendor/swir` staging-tree closure remain separate later gates.

## Why local manifests are rejected

Repo local manifests can add, replace or redirect source projects independently of the pinned upstream manifest. That flexibility is useful for normal Android development but is inappropriate for an evidence-producing SwirPhoneOS build unless the overlay is explicitly reviewed and represented in the repository. The dedicated evidence builder therefore rejects local-manifest state instead of silently synchronizing it.

This does not claim that every file in the Android checkout is clean. The resolved manifest, staging evidence, build identity and post-build source closure remain required. The workspace check only closes a high-impact persistent-runner injection path before synchronization begins.

## Why stale `out/` is rejected

The evidence path is intended to prove a fresh build result, not an incremental result that may reuse objects or images from a previous source revision. The preflight consequently requires an absent or empty `out/` tree.

The tool **never deletes** stale output. Cleanup is an operator action outside the evidence run and must be reviewed before retrying. This keeps the preflight read-only and prevents an automation error from recursively deleting an incorrectly configured path.

## Cuttlefish note

`cuttlefish_kvm_available` remains separately reported from source/build readiness. Runtime collection in the manual AOSP workflow additionally requires readable/writable `/dev/kvm` and a trusted absolute `adb` path. Passing the build preflight does not prove that Cuttlefish host packages, group membership, graphics acceleration or the produced `launch_cvd` runtime are functional; the runtime workflow must still launch the exact built product and obtain `sys.boot_completed=1` evidence.

## Privacy and bounded reporting

The JSON report does not publish the absolute workspace path or command paths. It stores a SHA-256 of the canonical workspace path as a local run identity and reports bounded booleans, the parsed Repo launcher version and free-space/inode metadata. It does not enumerate local-manifest filenames or Android source paths.

`cleanup_performed` is always `false`. A passing report is host/workspace readiness evidence only; it is not evidence that Android built, booted, passed Cuttlefish runtime checks, passed Treble/VTS, worked on physical hardware, or is safe to flash.

## Operator recovery

When the preflight rejects the builder:

1. inspect the failed check ID in `builder-preflight.json`;
2. for a missing host command or obsolete/unverifiable Repo launcher, repair the dedicated builder using the reviewed platform administration process rather than from inside the evidence workflow;
3. for a workspace hygiene failure, review the workspace manually and identify why the state exists;
4. remove or relocate only the specifically reviewed stale/local state outside the automation;
5. rerun the evidence workflow and preserve the resulting preflight, resolved manifest, staging report, build evidence and runtime evidence together.

Do not disable a gate just to make an evidence run pass. If a local manifest becomes a legitimate SwirPhoneOS dependency, represent that dependency explicitly in the checked-in platform/device build design and update the evidence contract in a reviewed change.

## Current project status

This hardening does not advance the weighted project milestone percentage. Until a real pinned Android 17 build completes, the exact SwirPhoneOS image boots, runtime evidence passes, and physical install/recovery gates are verified, project progress and Beta readiness remain unchanged.
