# Development instructions

Canonical repository: Swir/SwirPhoneOS. Do not edit KaliPhoneStudio, Konofix, SWIR OS Desktop or their automations as part of this project.

The existing task is `SwirPhoneOS Hourly`, ID `6aaa7889512c8191bf6f7137e45aa2a2`. Do not create a duplicate. Each scheduled run is a discrete engineering iteration, not continuous background computation. Inspect current main, recent commits/PRs, README/ROADMAP/CHANGELOG/BUILD_STATUS, beta gates and CI before modifying anything. Continue from repository state, not the earlier SwirOS ZIP.

Implement the largest coherent useful change that can actually be tested in the available run. Prioritize real OS/build integration and safe diagnostics over cosmetic commits. Use up-to-date primary upstream sources. Check file SHAs, preserve concurrent work and never force-push. Use a branch/PR for larger post-foundation changes and merge after final-head checks pass. Never claim an unperformed build/test, hardware result or release.

Repository-facing text is English; user reports are Polish. Future GUIs select system language with English fallback, support extensible translations, include a custom icon and `by Swir` with a GitHub link. Keep README/ROADMAP progress synchronized with progress.json; no hardware points from documentation or mocked tests. Keep a measurable OS roadmap, not only a desktop-tool roadmap.

Read-only first. No autonomous physical flashing or security bypass. No secrets or unlicensed blobs. No purchases/paid runners without separate permission. Beta publishing belongs to this same task and requires every condition in BETA_RELEASE_GATE.md for the exact build. Missing hardware/signing/build infrastructure blocks that gate, not all feasible engineering.

After each run report actual commit/PR, implemented changes, tests and pending CI honestly, roadmap points, beta blocker and next step. Do not send hourly ZIP archives.
