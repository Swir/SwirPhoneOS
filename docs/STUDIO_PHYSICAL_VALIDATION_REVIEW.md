# SwirPhoneStudio physical-validation review

SwirPhoneStudio has a fail-closed review layer for the current schema-v2 physical-device validation bundle produced by `swirphoneos.device_physical_validation`.

This review layer is deliberately **read-only and non-authorizing**. It validates one existing local JSON report, exposes only a bounded summary for Studio presentation, and preserves the exact report digest for operator correlation. It does not execute ADB or Fastboot, inspect a connected phone, install an image, change slots, write partitions, enable root, promote a device profile, or turn a review candidate into a supported-device claim.

## Accepted input

The selected file must be an absolute path to a non-empty regular `.json` file, must not be a symlink, and must remain within the Studio evidence size ceiling. The complete document is revalidated by `validate_physical_validation_report`, including:

- schema/provenance;
- exact profile/model/codename/current-build/target-build identity;
- distinct evidence bindings for every physical test and tracked capability;
- evidence verification projections;
- known capability failures and missing requirements;
- immutable `NOT_SUPPORTED` status;
- hard-false support, profile-promotion, install, write and root authorization;
- canonical SHA-256 integrity.

Malformed JSON, duplicate keys, oversized files, symlinks, forged authorization flags and digest drift fail closed.

## Main Studio surface

The main SwirPhoneStudio window exposes **Review device validation…** as a dedicated evidence action, with `Ctrl+P` as the keyboard shortcut. The action is disabled while a diagnostic session is running. Selecting a report never starts an ADB/Fastboot scan and never enables the diagnostic export path.

A successfully reviewed report replaces other temporary readiness-review views, is rendered into the existing report pane, and keeps report export disabled because the bounded review projection is not a diagnostic capture. Changing the Studio language re-renders the same already-validated summary without reopening or re-reading the evidence file.

Invalid or unsupported evidence shows only a localized generic failure message. Loader details, local paths and validation internals are not surfaced through the UI.

## Localized presentation

`swirphoneos.studio_physical_validation` converts only the bounded summary into the shared host localization system. EN/PL/NB/DE/ES/FR/PT/AR review copy is supplied as a data-only catalog fragment under `swirphoneos/locales/catalogs.d/`.

Machine-readable missing-requirement identifiers remain verbatim in the presentation so an operator can correlate the UI with the evidence file without translation ambiguity. Capability names and all surrounding prose use the selected Studio language.

## Current boundary

This package integrates the physical-validation reviewer into the main SwirPhoneStudio surface, but it does **not** claim that physical evidence exists for OnePlus Nord AC2003/avicii. The checked-in device profile remains `PLANNED_NOT_SUPPORTED`, weighted engineering progress remains governed by `project.json`, and physical/reference-hardware beta gates stay open until real exact-device evidence is captured and reviewed.

The review button is evidence presentation only. It cannot promote support, authorize installation, authorize a device write, unlock a bootloader, enable SwirRoot, or satisfy a beta gate by itself.
