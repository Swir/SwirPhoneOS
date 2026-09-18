# Swir Gallery album browsing

Swir Gallery now has a bounded source-stage album browser built on Android MediaStore bucket metadata. It groups only the media already visible through the app's reviewed `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` permissions and lets the owner switch between all loaded media and a specific album without adding storage, network or write permissions.

## Safety boundary

- Album identity comes from `BUCKET_ID`; the displayed label comes from `BUCKET_DISPLAY_NAME` and is stripped of control characters and capped at 80 characters.
- The existing media query remains bounded to 300 visible image/video rows.
- Album search extends the existing local name/MIME filter; it does not contact a server or inspect unrelated files.
- Deletion still uses Android's owner-confirmed `MediaStore.createDeleteRequest` flow.
- No `ContentResolver.insert`, `update` or direct `delete` path is introduced.
- No broad storage permission, legacy external-storage permission, process execution or network primitive is added.

## Verification status

The pure-Java album policy is host-tested and the source contract has a dedicated regression test covering MediaStore bucket use, the exact two-permission allowlist, read-only boundaries and localization parity across EN/PL/NB/DE/ES/FR/PT/AR. Essential-source CI compiles and runs the Gallery policy test.

This remains **source-stage only**. The project capability ledger is intentionally not promoted by this change: real Android build/runtime behavior, rendered layout, large-library behavior and accessibility still require the pinned SwirPhoneOS Cuttlefish evidence chain. This work does not change weighted project progress, beta gates, hardware support or release readiness.
