# AOSP builder admission

This is the lightweight, read-only admission step for the dedicated SwirPhoneOS Android build host. Run it before spending hours on the full `AOSP build evidence` workflow.

## What it proves

The manual **AOSP builder admission** workflow targets the same self-hosted runner labels and the same `swir-aosp-builder` concurrency lock as the full build. It executes the checked-in `swirphoneos build-preflight` contract and requires the host to be ready for a full build. By default it also requires readable and writable KVM so the same host can later collect Cuttlefish runtime evidence.

The report checks the current host and workspace facts used by the full build gate, including Linux x86-64, supported glibc, required tools, Repo launcher version, RAM, free workspace capacity, requested parallel-job budget and reviewed workspace cleanliness. The runner must provide an absolute `SWIR_AOSP_WORKSPACE`. A successful admission also captures a separate exact host/toolchain identity snapshot (`aosp-host-admission.json`).

The full **AOSP build evidence** workflow downloads that exact admission artifact before touching the persistent AOSP workspace. Its existing admission-gate command now re-captures the current host read-only and requires exact workspace, static-host and required-tool-byte continuity against `aosp-host-admission.json`. It also rechecks the current 64 GiB RAM and 400 GiB free-space floors from the build preflight, and requires KVM to still be available when runtime collection was requested. Any drift rejects the run before `repo init`, `repo sync`, staging or compilation.

## Safety boundary

Admission and freshness verification are intentionally smaller than the build workflow. Admission does not sync Android source and does not write to a phone; neither step performs any AOSP workspace mutation before the freshness gate passes. Together they:

- do not stage SwirPhoneOS into the AOSP workspace;
- do not compile AOSP;
- do not launch Cuttlefish;
- do not invoke `adb` or `fastboot`;
- do not install host packages or clean the workspace.

A green admission or freshness gate is **not build evidence** and is **not boot evidence**. It only proves that the dedicated builder satisfies the checked-in host/workspace prerequisites and that the exact admitted host/toolchain identity has not drifted before the build window. The canonical build, boot and runtime evidence must still come from the separate **AOSP build evidence** workflow and its bound artifacts.

## First-run procedure

1. Register a dedicated Linux x86-64 self-hosted runner with the `swir-aosp-builder` label.
2. Configure an owner-controlled absolute `SWIR_AOSP_WORKSPACE` on that runner.
3. Install the host prerequisites documented in `docs/AOSP_BUILD_WORKSPACE.md`; enable KVM if Cuttlefish evidence is expected.
4. Dispatch **AOSP builder admission** with the intended AOSP parallel-job count. Keep `require_kvm=true` for the normal build-plus-runtime path.
5. Inspect the uploaded `SwirPhoneOS-aosp-builder-admission` artifact containing the bounded preflight, run attestation and exact host/toolchain identity snapshot. A rejected host must be fixed rather than bypassed.
6. Only after admission succeeds, dispatch **AOSP build evidence** for the same exact commit and job budget. The build admission gate rechecks the downloaded host snapshot against the current builder before source synchronization begins.

The admission artifact and freshness check are bounded host/workspace evidence. They never change `project.json`, never promote a beta gate and never turn source-only validation into device support.
