# Swir Clock world-time source contract

Swir Clock now includes a source-stage, permission-free world-clock surface in addition to local time, stopwatch, timer and the explicit Android alarm hand-off.

## Reviewed behavior

The checked-in pure-Java `ClockCore` owns a bounded inventory of five IANA time-zone IDs: `UTC`, `Europe/Oslo`, `Europe/Warsaw`, `America/New_York` and `Asia/Tokyo`. The Android activity lets the owner cycle through that reviewed inventory and renders both the localized zone display name and localized short time. Zone calculations use `java.time.ZoneId`/`ZonedDateTime`; invalid zone identifiers and out-of-range selection indexes fail closed.

The owner-selected zone index is stored only in the app's private `SharedPreferences`. On startup the saved value is passed through `ClockCore.safeWorldZoneIndex`; a corrupt or obsolete index falls back to index `0` (`UTC`) rather than indexing outside the reviewed inventory. Changing the selection writes only the bounded integer preference.

The world-clock control does not request network, location, calendar, alarm or storage permissions. It does not infer location. The owner changes the shown zone explicitly.

## Localization

The owner-visible world-clock title and accessibility description are resource-backed in the same eight source catalogs as the rest of Swir Clock: English, Polish, Norwegian Bokmål, German, Spanish, French, Portuguese and Arabic. Zone names come from the platform time-zone database using the active locale. The localization contract test requires every supported catalog to expose exactly the same string-key inventory.

## Verification boundary

`ClockCoreHostTest` exercises the exact reviewed zone inventory, saved-index fallback, wraparound behavior, invalid-index rejection, invalid-IANA-zone rejection, UTC/Tokyo time conversion and localized zone labels. `tests/test_clock_world_clock.py` additionally checks the Android source wiring, private preference persistence, permission boundary and all eight catalogs.

This is **source-stage evidence only**. It does not prove Android compilation, rendered layout quality, timezone-database behavior on the target AOSP build, alarm-provider behavior, accessibility quality, Cuttlefish runtime or physical-device behavior. Swir Clock therefore remains `ANDROID_SOURCE`; this work does not satisfy a beta gate or increase weighted OS progress.
