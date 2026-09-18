# SwirPhoneOS shared Android design system

SwirPhoneOS carries a source-stage Android resource library named `SwirDesign`. It is the common visual contract for the complete first-party system-app suite and remains deliberately separated from Android build/runtime claims.

## Scope

All twenty current first-party system applications statically link the same `SwirDesign` Android resource library and declare the same `Theme.SwirPhoneOS` application theme:

- Swir Phone
- Swir Messages
- Swir Camera
- Swir Calculator
- Swir Settings
- Swir Files
- Swir Browser
- Swir Device Care
- Swir Update
- Swir Privacy
- Swir Clock
- Swir Notes
- Swir Calendar
- Swir Weather
- Swir Gallery
- Swir Recorder
- Swir Contacts
- Swir Backup
- Swir Apps
- SwirRoot

This is meaningful source integration, but it is not proof that the final AOSP image builds, that the shared theme renders correctly on Cuttlefish, or that accessibility and visual review are complete. `all_system_apps_integrated=true` therefore describes source-stage theme integration only; `android_build_verified`, `runtime_visual_review_verified` and `accessibility_review_verified` remain false until real evidence exists.

## Direct token-migration cohort

Theme inheritance alone is not enough to produce a coherent product if individual activities continue to hardcode their own palettes and touch geometry. The current direct token-migration cohort is:

- Swir Phone
- Swir Messages
- Swir Camera
- Swir Settings
- Swir Files
- Swir Browser
- Swir Update
- Swir Privacy
- Swir Device Care

These activities now use shared Swir background/text/accent/surface resources and the common 48 dp minimum touch-target token instead of direct `android.graphics.Color` literals for their primary UI surfaces. Their existing functional and safety behavior remains explicit: Phone still performs `ACTION_DIAL`, Messages still performs `ACTION_SENDTO`, Camera keeps its source-stage capability/capture hand-off, Settings and Privacy route only to reviewed Android settings actions, Update remains read-only with package installation disabled, Device Care remains a permission-free framework diagnostics surface, Files remains a Storage Access Framework manager limited to user-granted document trees, and Browser keeps HTTPS-first WebView policy while its download flow uses an app-scoped DownloadManager destination without broad storage permission or WebView-cookie forwarding.

All five beta-critical core applications are directly tokenized at source stage: Settings, Files, Update, Privacy and Device Care. This satisfies the source-only `all_core_apps_tokenized=true` design-contract condition, but it does **not** grant Android runtime, visual-review, accessibility, emulator, device-support or beta milestone credit. The remaining applications stay theme-integrated but are not claimed as fully tokenized unless they belong to the explicit direct-token cohort above.

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

The default palette is light and `values-night` supplies the dark electric-cyan SwirPhoneOS palette. Both variants must expose the exact same named color/style inventory. This makes theme-mode changes data-driven and keeps app logic from owning palette selection.

## Build integration

`SwirDesign` is an `android_library` with `sdk_version: "current"`, `min_sdk_version: "35"` and `product_specific: true`. All twenty apps link it through Soong `static_libs`, so shared resources are merged at build time rather than installed as a separate user-visible package.

The six reviewed design-source files are included in `stage_manifest.d/design.json`, preserving the existing exact-tree `vendor/swir/` staging model. The design contract does not weaken source closure, product identity, package-set, permission, build-evidence, device-support or SwirRoot gates.

## Fail-closed host contract

`swirphoneos.design_contract.validate_design_contract()` uses design contract v4 and verifies:

1. the exact SwirDesign module identity and build properties;
2. day/night token parity;
3. the exact spacing/touch-target token inventory;
4. the shared theme/style inventory;
5. static-library linkage from all twenty system applications;
6. exact `Theme.SwirPhoneOS` manifest usage for all twenty applications;
7. direct shared-token usage and no `android.graphics.Color` literals across the nine-app tokenized cohort;
8. complete source-stage token coverage of all five beta-critical core applications, including Swir Files;
9. exact staging-file and destination inventory with duplicate-key rejection.

Its public summary separates complete source-stage theme integration, the nine-app direct-token cohort and the complete five-app beta-core token cohort. Android build, runtime visual review, accessibility review and device-write authorization remain false.

## Swir Files migration boundary

Swir Files is a larger activity than the earlier Settings/Update/Privacy/Device Care token pilots, so its migration is intentionally limited to presentation and accessibility geometry. The Storage Access Framework tree grant, persisted URI permission, browse/search, copy/move, rename, create-folder, share/open and owner-confirmed delete flows are unchanged. The migration replaces activity-owned day/night assumptions with shared theme colors, adds the shared 48 dp minimum height to the search field and generated action/file-row buttons, and keeps locale-direction handling through `LAYOUT_DIRECTION_LOCALE`.

The host contract fails if Swir Files regresses to direct `android.graphics.Color` use or stops referencing the common touch-target token. These checks are source guards only; they cannot prove provider-specific runtime behavior, screen-reader quality or rendering on a built image.

## Swir Browser migration boundary

Swir Browser now uses the same background, text, surface, spacing and 48 dp touch-target resources as the direct-token cohort. The migration does not relax its networking policy. JavaScript remains off by default, file/content access remains disabled, mixed content remains blocked and third-party cookies remain disabled.

The Browser download flow is separately documented in `SWIR_BROWSER_DOWNLOADS.md`. Source guards require an explicit HTTPS entry URL, sanitized bounded filenames, bounded MIME metadata, an app-specific DownloadManager destination and an owner-visible downloads surface. They also reject copying WebView cookies into requests or switching to a public-external destination helper. Runtime redirect behavior is not inferred from these source checks.

## Runtime review still required

No visual milestone credit is earned by this source work alone. After the first real SwirPhoneOS build and Cuttlefish boot, the complete app suite must be reviewed for at least:

- correct light/dark palette selection;
- status/navigation bar legibility;
- contrast and readable text;
- text expansion in every supported locale;
- Arabic RTL mirroring;
- minimum practical touch targets;
- TalkBack/focus order and content descriptions;
- no clipped controls at supported density/font-scale combinations;
- consistency between theme-driven apps and directly tokenized screens.

Only real build/runtime evidence and interactive review can promote the shared design work beyond source stage. Weighted project progress therefore remains unchanged until those gates are satisfied.
