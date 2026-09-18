# Swir Calendar provider bridge and local ICS import

Swir Calendar keeps its authoritative first-party agenda in app-private SQLite while adding two explicit interoperability surfaces: bounded owner-selected iCalendar import and an owner-visible hand-off to an installed Android calendar application. Both paths are source-stage only and do not claim Android runtime compatibility.

## Local calendar import

The import flow uses `ACTION_OPEN_DOCUMENT` with `CATEGORY_OPENABLE` and `text/calendar`. The selected document is opened read-only through the Storage Access Framework. Input is capped at 64 KiB before decoding, decoded as strict UTF-8, and parsed by dependency-free `EventPolicy` code before anything is inserted into the local agenda.

The parser intentionally supports a narrow single-event subset rather than attempting to silently normalize arbitrary calendars. It accepts one `VCALENDAR` containing one `VEVENT`, UTC date-time values (`yyyyMMdd'T'HHmmss'Z'`) or all-day dates (`yyyyMMdd`), bounded title/location values, standard escaped text, and folded lines. Duplicate critical fields, malformed times, multiple events/calendars, trailing non-empty content, unsupported ambiguous local date-times, invalid escapes and non-positive event duration fail closed. Missing end time becomes one hour for timed events or one day for all-day events.

The parser performs no network access, provider access, recurrence expansion, alarm import or attachment retrieval. Imported events become local Swir Calendar records only.

## Device calendar hand-off

A local event can be sent to the platform calendar surface with an explicit `Intent.ACTION_INSERT` targeting `CalendarContract.Events.CONTENT_URI`. Swir Calendar supplies title, location, begin time and end time as intent extras, verifies that an activity can resolve the request, and then lets the owner review and confirm the final provider-side write in the external calendar UI.

Swir Calendar requests neither `READ_CALENDAR` nor `WRITE_CALENDAR`. It does not call `ContentResolver.insert`, `update` or `delete` against `CalendarContract.Events`. The source contract and regression tests reject any drift toward silent provider mutation.

This means `calendar:provider_bridge` is source-implemented as an owner-visible interoperability hand-off. It is not evidence that every Android calendar provider accepts the intent, persists all fields correctly or behaves consistently on supported hardware.

## Shared SwirPhoneOS design and localization

The Calendar activity now consumes the shared `SwirDesign` resource palette, spacing and minimum touch-target dimensions instead of local hard-coded colors. The new import and device-calendar hand-off surface is localized in EN/PL/NB/DE/ES/FR/PT/AR and remains RTL-aware through the existing application configuration.

## Verification boundary

Host/source verification covers the pure-Java import policy, permission inventory, owner-visible provider hand-off tokens, absence of direct provider writes, bounded strict-UTF-8 import, shared design-token usage and identical localization key sets. The Essential source suite compiles and executes `EventPolicyHostTest`.

Runtime evidence is still mandatory. A built SwirPhoneOS image must exercise SAF import, local persistence, exported ICS round-trips, intent resolution, external calendar confirmation, RTL rendering and accessibility before any stronger runtime claim. This work does not change weighted project progress, beta gates, device support, install/rollback status or release readiness.
