# Changelog

## 0.0.2.dev0 — 2026-09-16 — Developer foundation, no release

### Read-only Flash Studio desktop slice

Added a runnable Python/Tk desktop companion with dark blue styling, the project icon, trusted ADB file selection, asynchronous read-only inspection, elapsed status, read-only report display, create-only local JSON export and the `by Swir` GitHub footer. Added extensible English, Polish and Norwegian Bokmal catalogs with native language detection and English fallback. The GUI never invokes Tk from the worker thread. Duplicate scans are rejected, failed scans invalidate previous exports, and raw exception details stay private. Export validation rejects extra fields, changed safety/provenance flags and invalid values; existing files and target symlinks are not overwritten. Reports do not upload automatically.

Added 46 desktop tests, including 7 real Tk-window tests with synthetic inspection. All 46 passed locally on Linux/Python 3.13.5. Added native Linux/Windows GUI smoke checks to the existing Python 3.11–3.14 CI matrix. This is source-level desktop runtime work, not an EXE, Android image or physical-phone validation. Progress remains 2%; beta gates remain 0/9.

### Initial foundation

Migrated the mobile SwirOS foundation direction to the canonical `Swir/SwirPhoneOS` repository. Added executable read-only ADB diagnostics with an explicit trusted-tool path, command allowlist, single-device selection, private errors, unknown-state handling and endpoint recheck. Added weighted progress accounting, strict mandatory beta-gate validation and a hard publication guard. Added 41 local host tests and a Windows/Linux Python 3.11–3.14 CI matrix with SHA-pinned Actions and read-only permissions. Added an original vector application icon, architecture, safety policy, development instructions and an explicitly unsupported avicii metadata profile.

The initial foundation did not include a GUI; the desktop slice above adds it. No Android image, live-phone validation, Windows EXE or installation/restore capability is claimed.

## 0.0.1 — Initial concept archive

The earlier SwirOS ZIP contained planning documentation. It was not a bootable OS, installer or hardware-supported release. Its scope is continued here with corrected safety and readiness distinctions.
