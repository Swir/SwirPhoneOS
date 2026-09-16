# Beta Release Gate

**Status: BLOCKED. No beta release is authorized by the current evidence.**

User authorization permits publishing a GitHub prerelease once the following conditions are genuinely met. It does not authorize unattended phone flashing. Beta publication is part of the existing hourly development task, not a second automation.

Every result must refer to the same candidate commit, built image manifest/checksums, exact device profile and firmware baseline. Each result needs its actual test method, environment, date and sanitized evidence. A maintainer must review evidence; a checkbox or success flag is not proof. No private identifiers, keys or unrestricted raw logs belong in public evidence.

- [ ] Reproducible, bootable SwirPhoneOS image from an identified source revision.
- [ ] Physical AC2003/avicii boot with exact firmware baseline recorded.
- [ ] Usable UI, display/touch, calls/SMS/data, Wi-Fi/Bluetooth and intended connectivity scope.
- [ ] Audio/microphone, camera, storage and required sensors validated with limitations disclosed.
- [ ] Encryption/security configuration and safe charging, thermals and suspend verified; no critical blocker.
- [ ] Installation AND recovery/stock-restore procedures tested on the exact profile.
- [ ] Actual Windows Flash Studio executable built and runtime-smoke-tested.
- [ ] All relevant CI checks pass on the final candidate, not an earlier revision.
- [ ] Distributable artifacts, signatures/authenticity and SHA-256 manifest verified.
- [ ] English installation/recovery instructions, supported variants and known issues match the artifacts.

Missing today: all ten gates. No Android image has been built or booted; no physical device is connected; no installation/recovery procedure or Windows executable has been runtime-tested; release signing is not configured.

When all gates pass, publish a versioned **prerelease** with the actual permitted system images, Windows package, checksums and English notes. Re-read the release and assets to confirm publication, then report in Polish. Do not publish an empty release, a source-only archive or a host utility as a completed OS beta. Never infer readiness from roadmap percentage alone.
