# Build status

Version: **0.0.1-dev**. Stage: **host foundation only**. Beta: **BLOCKED**.

## Verified locally on 2026-09-16

Linux, Python 3.13.5: 19 tests passed (16 offline preflight tests and 3 repository contract tests). Tests use synthetic properties; no phone was contacted. The CLI returns exit 2 with explicit blockers for the bundled synthetic example. This proves bounded input handling and fail-closed reporting, not hardware support.

GitHub CI is configured for Ubuntu/Windows and Python 3.11-3.14. Its run status is available in Actions; configuration is not evidence that every job passed. Compilation/import and roadmap consistency checks are included. No Android build job is claimed.

## Not built or verified

AOSP source lock/build, emulator boot, physical boot, kernel/vendor compatibility, live USB detection, backup, installation, stock restore, OTA, Windows EXE and release signing. OnePlus Nord AC2003/avicii remains PLANNED / NOT SUPPORTED.
