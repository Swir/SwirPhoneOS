# SwirPhoneOS shared Android design system

SwirPhoneOS now carries a source-stage Android resource library named `SwirDesign`. It is the first common visual contract for the beta-critical core applications and is deliberately separated from runtime claims.

## Scope

The first integration cohort is:

- Swir Settings
- Swir Files
- Swir Update
- Swir Privacy
- Swir Device Care

These five applications statically link the same `SwirDesign` Android resource library and use the same `Theme.SwirPhoneOS` application theme. This is meaningful source integration, but it is not proof that the final AOSP image builds, that the theme renders correctly on Cuttlefish, or that accessibility and visual review are complete.

The other bundled applications retain their current source-stage UI until they are migrated and reviewed. `all_system_apps_integrated=false` therefore remains part of the host design-contract report.

## Visual tokens

The source contract defines a compact, original SwirPhoneOS token set:

- background, surface and alternate-surface colors;
- electric-blue/cyan accents;
- primary and secondary text colors;
- outline, error and success colors;
- shared spacing from 4 dp to 32 dp;
- corner-radius tokens;
- a 48 dp minimum touch-target token;
- shared headline/body/secondary text appearances.

The default palette is light and `values-night` supplies the dark electric-cyan SwirPhoneOS palette. Both variants must expose the exact same named color/style inventory. This makes theme-mode changes data-driven and prevents a language or app-specific logic path from deciding colors directly.

## Build integration

`SwirDesign` is an `android_library` with `sdk_version: "current"`, `min_sdk_version: "35"` and `product_specific: true`. Core apps link it through Soong `static_libs`, so the shared resources are merged at build time rather than installed as a separate user-visible package.

The six reviewed design-source files are included in `stage_manifest.d/design.json`, preserving the existing exact-tree `vendor/swir/` staging model. The design contract does not weaken source closure, product identity, package-set or build-evidence gates.

## Fail-closed host contract

`swirphoneos.design_contract.validate_design_contract()` verifies:

1. the exact SwirDesign module identity and build properties;
2. day/night token parity;
3. the exact spacing/touch-target token inventory;
4. the shared theme/style inventory;
5. static-library linkage from every core app in the first cohort;
6. exact `Theme.SwirPhoneOS` manifest usage;
7. exact staging-file and destination inventory with duplicate-key rejection.

Its public summary remains explicit that Android build, runtime visual review, accessibility review and all-system-app integration are not yet verified.

## Runtime review still required

No visual milestone credit is earned by this source work alone. After the first real SwirPhoneOS build and Cuttlefish boot, the core cohort must be reviewed for at least:

- correct light/dark palette selection;
- status/navigation bar legibility;
- contrast and readable text;
- text expansion in every supported locale;
- Arabic RTL mirroring;
- minimum practical touch targets;
- TalkBack/focus order and content descriptions;
- no clipped controls at supported density/font-scale combinations.

Only runtime evidence and interactive review can promote the shared design work beyond source stage.
