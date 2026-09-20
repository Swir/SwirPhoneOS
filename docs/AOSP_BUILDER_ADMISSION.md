# AOSP builder admission

This is the lightweight, read-only admission step for the dedicated SwirPhoneOS Android build host. Run it before spending hours on the full `AOSP build evidence` workflow.

## What it proves

The manual **AOSP builder admission** workflow targets the same self-hosted runner labels and the same `swir-aosp-builder` concurrency lock as the full build. It executes the checked-in `swirphoneos build-preflight` contract and requires the host to be ready for a full build. By default it also requires readable and writable KVM so the same host can later collect Cuttlefish runtime evidence.

The report checks the current host and workspace facts used by the full build gate, including Linux x86-64, supported glibc, required tools, Repo launcher version, RAM, free workspace capacity, requested parallel-job budget and reviewed workspace cleanliness. The runner must provide an absolute `SWIR_AOSP_WORKSPACE`.

## Safety boundary

Admission is intentionally smaller than the build workflow. It:

- does not sync Android source;
- does not stage SwirPhoneOS into the AOSP workspace;
- does not compile AOSP;
- does not launch Cuttlefish;
- does not invoke `adb` or `fastboot`;
- does not install host packages or clean the workspace;
- does not write to a phone.

A green admission is **not build evidence** and is **not boot evidence**. It only removes uncertainty about whether the dedicated builder satisfies the checked-in host/workspace prerequisites. The canonical build, boot and runtime evidence must still come from the separate **AOSP build evidence** workflow and its bound artifacts.

## First-run procedure

1. Register a dedicated Linux x86-64 self-hosted runner with the `swir-aosp-builder` label.
2. Configure an owner-controlled absolute `SWIR_AOSP_WORKSPACE` on that runner.
3. Install the host prerequisites documented in `docs/AOSP_BUILD_WORKSPACE.md`; enable KVM if Cuttlefish evidence is expected.
4. Dispatch **AOSP builder admission** with the intended AOSP parallel-job count. Keep `require_kvm=true` for the normal build-plus-runtime path.
5. Inspect the uploaded `SwirPhoneOS-aosp-builder-admission` JSON artifact. A rejected host must be fixed rather than bypassed.
6. Only after admission succeeds, dispatch **AOSP build evidence** for the pinned Android 17 baseline.

The admission artifact is bounded host/workspace evidence. It never changes `project.json`, never promotes a beta gate and never turns source-only validation into device support.
