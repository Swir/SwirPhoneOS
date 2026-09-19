# Swir Apps — Local Update Provenance

Swir Apps exposes a local, read-only view of installed launcher applications. The update-provenance surface is intentionally narrower than a full app-store update service: it helps the owner understand how an installed package is maintained without enabling downloads, installs, package replacement, privileged writes, or network update checks.

## Owner-visible metadata

For each visible launcher application, Swir Apps shows:

- package name and installed version;
- a bounded SHA-256 signing-certificate fingerprint preview;
- an update-path classification derived from Android package metadata;
- the package's recorded last-update timestamp formatted with the active locale.

The update-path classification is fail-closed:

- `SYSTEM_IMAGE` when Android marks the package as a system or updated-system package;
- `EXTERNAL_INSTALLER` only when Android reports a syntactically valid installing package name;
- `LOCAL_UNKNOWN` when no trustworthy installer identity is available.

The classification is descriptive provenance, not an assertion that an update is available. Swir Apps does not contact an update server and does not compare remote versions.

## Safety boundary

This source stage does **not** use `DownloadManager`, `PackageInstaller`, `ACTION_INSTALL_PACKAGE`, `REQUEST_INSTALL_PACKAGES`, Internet access, shell/process execution, ADB/Fastboot, or any device-write path. Selecting an app still launches the installed package, while long-press opens Android's authoritative application-details screen.

`apps:update_status` remains intentionally uncredited in the source capability ledger. A real update-status implementation still needs a reviewed source of update availability/version policy and later Android runtime validation. Local install-source and timestamp metadata alone must not be promoted into an update-available claim.

## Localization and validation

All owner-facing update-provenance strings are present in the canonical EN catalog plus PL/NB/DE/ES/FR/PT/AR catalogs. Python source-contract tests reject install/network primitives and require the Android metadata surface. The dependency-free `AppCatalogPolicyHostTest` verifies classification and timestamp normalization and is compiled/executed when a JDK is available.

This work is source-stage only. It does not prove an AOSP build, Cuttlefish runtime, update delivery, package installation, physical-device support, or Beta readiness.
