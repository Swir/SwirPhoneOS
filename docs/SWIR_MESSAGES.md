# Swir Messages source-stage handoff boundary

Swir Messages is a first-party SwirPhoneOS compose surface. Its current source-stage design keeps the final carrier send outside the app until the exact Android runtime, messaging role/provider integration and reference-device telephony stack are validated.

## Text compose

- Recipients and body are normalized and bounded by pure-Java `MessagePolicy`.
- The owner explicitly continues with an `ACTION_SENDTO` `smsto:` intent.
- Swir Messages does not request `SEND_SMS`, `READ_SMS` or `RECEIVE_SMS` and does not call `SmsManager`.
- A successful handoff means only that Android accepted the compose intent. It does not prove send, delivery, receipt or conversation history.

## Owner-selected media compose

The source now supports an optional, owner-selected image, video or audio attachment through the Storage Access Framework.

The attachment must:

- arrive from `ACTION_OPEN_DOCUMENT` as a `content://` URI;
- report an `image/*`, `video/*` or `audio/*` MIME type;
- have a safe bounded display name;
- have a known positive size no larger than 25 MiB.

If those checks pass, the app creates a visible Android `ACTION_SEND` share intent with the selected content URI, a read-only URI grant, the normalized recipients/body metadata and an explicit chooser. Swir Messages neither copies the media into broad shared storage nor requests media/storage/network permissions. Unsupported or incomplete provider metadata fails closed.

This is a **media-message compose handoff**, not a claim of working carrier MMS. The registry capability `messages:mms` therefore remains open until the pinned SwirPhoneOS image is built and the exact runtime messaging app/provider/carrier behavior is reviewed.

## Local handoff history

Recent handoff history remains optional and disabled by default. It stores a bounded local record only for text compose handoffs. Media bytes, delivery status and conversations are not stored or inferred.

## Runtime gates still required

Before any runtime capability promotion, test at minimum:

1. text handoff resolution and recipient/body preservation;
2. media picker denial/cancel/error handling;
3. image/video/audio URI grants and chooser behavior;
4. attachment-only compose and text-plus-attachment compose;
5. size/MIME/provider-metadata rejection;
6. default messaging app and carrier MMS behavior on the exact build;
7. EN/PL/NB/DE/ES/FR/PT/AR layout, text expansion, accessibility and Arabic RTL;
8. process recreation and URI-grant behavior;
9. privacy review confirming no silent-send/provider-history path was introduced.

Until those runtime checks exist, Swir Messages remains `ANDROID_SOURCE`, not `ANDROID_RUNTIME` or hardware verified.
