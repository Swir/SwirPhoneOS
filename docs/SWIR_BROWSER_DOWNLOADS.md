# Swir Browser download boundary

Swir Browser implements a source-stage download flow using Android `DownloadManager` without adding broad storage permissions.

## Reviewed behavior

- A WebView download callback is accepted only when the original download URL has an explicit `https` scheme and passes the existing bounded URL policy.
- The suggested filename is sanitized by pure-Java policy code: control/path-reserved characters are replaced, dot-only or empty names fall back to `download.bin`, and names are capped at 120 characters while preserving a short extension where practical.
- MIME metadata is optional and accepted only when it matches a bounded token/token shape. Parameterized or malformed values are discarded rather than forwarded.
- Files are directed to `DownloadManager.Request.setDestinationInExternalFilesDir(..., Environment.DIRECTORY_DOWNLOADS, ...)`, keeping the source-stage flow in app-specific external storage. Swir Browser still requests only `android.permission.INTERNET`.
- The owner can open Android's downloads surface explicitly with `DownloadManager.ACTION_VIEW_DOWNLOADS`.
- WebView cookies are deliberately **not** copied into download request headers. Authenticated downloads that require a WebView session may therefore fail until a separate reviewed credential/session bridge exists.

## Security boundary

The source contract rejects HTTP, scheme-less, `file:`, `data:` and `javascript:` download entry URLs. It also fails closed if the activity starts copying WebView cookies, switches to the public-external destination helper, or loses the app-scoped DownloadManager flow.

This gate validates the entry URL only. Redirect handling after enqueue is owned by Android DownloadManager and has not yet been runtime-verified on a built SwirPhoneOS image. The project therefore does not claim end-to-end HTTPS redirect enforcement from source inspection alone.

## Status

The `downloads` capability is source-implemented and host-policy tested, but Swir Browser remains `ANDROID_SOURCE`. No Cuttlefish runtime, visual/accessibility review, download-manager integration smoke, or physical-device behavior is claimed by this work. Weighted project progress and beta readiness do not change.
