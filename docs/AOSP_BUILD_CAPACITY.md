# AOSP build-capacity guard

SwirPhoneOS uses a dedicated self-hosted runner for evidence-producing AOSP builds. The existing workflow exports the requested parallel job count as `SWIR_REQUESTED_JOBS` before `python -m swirphoneos build-preflight` runs.

The preflight now applies a conservative **SWIR operational safety guard** when that request is present:

- the request must be an integer from 1 through 256;
- the host must expose a positive logical CPU count;
- total host RAM must be known;
- the safe ceiling is `min(logical CPUs, floor(total RAM / 4 GiB), 256)`;
- a request above that ceiling keeps `ready_for_source_sync=true` when the source-sync requirements otherwise pass, but forces `ready_for_full_build=false` and fails `parallel_jobs_within_host_budget`.

The 4 GiB-per-job rule is intentionally a project safety policy, **not an Android/AOSP host requirement**. The separately documented AOSP host floor remains 64 GiB RAM and 400 GiB free disk for this evidence workflow. On a 64 GiB / 32-thread builder, for example, the safety ceiling is 16 jobs, matching the workflow default.

Local preflight callers that do not export `SWIR_REQUESTED_JOBS` retain the previous host-readiness behavior. This avoids turning an informational local check into a build-scheduling decision. Evidence-producing workflow runs do export the request and therefore fail closed when CPU/RAM capacity cannot be established.

This guard does not start a build, alter the runner, install dependencies, clean the workspace, configure KVM, write to a phone, or grant any project milestone/beta credit. A successful preflight still requires a real pinned-source build and the existing evidence chain before `aosp_baseline`, `emulator_boot`, device support, or beta readiness can advance.
