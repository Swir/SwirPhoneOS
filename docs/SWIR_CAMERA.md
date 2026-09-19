# Swir Camera engineering contract

Swir Camera is the first-party capture application for SwirPhoneOS. The repository currently contains meaningful **Android source-stage** Camera2 photo capture plus a direct H.264/MP4 video path, but neither path is promoted to Android-runtime or hardware-verified status until the pinned SwirPhoneOS image builds, boots and is reviewed on the exact target runtime/device.

## Current permission boundary

Swir Camera requests exactly:

```text
android.permission.CAMERA
```

It does not request microphone, network, broad-storage or media-write permissions. Direct source-stage video is intentionally silent so adding video cannot silently widen the privacy boundary to `RECORD_AUDIO`.

## Photo path

Owner-triggered still capture uses Camera2 and an `ImageReader` JPEG surface. The output is written through a scoped pending MediaStore row under `Pictures/SwirPhoneOS`; failed writes delete the pending row. Front/back selection and JPEG orientation are derived from reviewed camera/display state. Runtime camera quality and exact-device behavior remain unverified.

## Direct video path

When the selected camera reports a usable encoder surface, the source-stage path:

- creates an AVC/H.264 `MediaCodec` input surface;
- uses a bounded 30 fps policy and bounded bitrate;
- accepts only positive, even-sized video dimensions up to 3840 × 2160;
- drives Camera2 with `TEMPLATE_RECORD` and continuous-video autofocus;
- muxes into MP4 through `MediaMuxer`;
- applies an orientation hint from the reviewed sensor/display orientation policy;
- writes to a pending scoped MediaStore row under `Movies/SwirPhoneOS`;
- publishes the row only after encoder EOS and successful muxer finalization;
- deletes the pending row on setup/finalization failure.

If the camera does not expose a direct encoder surface, the video button keeps an owner-visible `ACTION_VIDEO_CAPTURE` fallback instead of silently inventing support.

## Lifecycle safety

Direct recording uses an explicit setup/record/finalize transition guard. A second start cannot overlap an existing pending video row, encoder or drain thread. Setup and finalization disable conflicting capture/lens controls. Camera loss and activity teardown trigger fail-closed cleanup. After EOS is requested, encoder finalization is bounded by a five-second monotonic timeout so a broken encoder cannot retain the pending row and codec resources indefinitely.

These guards are source-level safety measures only. They do not prove a device camera HAL accepts the surface combination, that the chosen codec profile is available, that frames are encoded correctly, or that the produced MP4 has acceptable quality.

## Source validation

The focused source tests enforce:

- exact CAMERA-only permission scope;
- H.264/MP4 `MediaCodec` + `MediaMuxer` primitives;
- no hidden `MediaRecorder` or audio permission path;
- scoped pending MediaStore video persistence;
- visible Android fallback when direct encoding is unavailable;
- even-dimension, resolution and bitrate bounds;
- serialized setup/record/finalize state and bounded finalization;
- EN/PL/NB/DE/ES/FR/PT/AR resource-key parity.

`CameraPolicyHostTest` executes the dependency-free dimension/bitrate/orientation policy on the host. Essential source CI runs both the Java policy test and the focused direct-video Python boundary test.

## Runtime validation required before capability promotion

`camera:video_capture` remains open. Promotion requires the exact built SwirPhoneOS candidate and at minimum:

1. Cuttlefish build/launch evidence for the Swir Camera package, without treating emulator media behavior as physical-camera proof.
2. Runtime CAMERA permission denial/grant review and activity lifecycle checks.
3. Direct-record start/stop, repeated-tap and background/foreground cleanup tests.
4. Successful MediaStore publish plus failure-path pending-row cleanup.
5. Rotation/orientation review for supported display orientations.
6. Front/back camera switching and unsupported-direct-surface fallback review.
7. Exact-device validation of camera HAL stream combinations, encoder availability, video integrity, frame pacing, thermal behavior and storage behavior.
8. Known limitations recorded for each supported build/profile before beta claims.

Audio capture is a separate future product decision. It must not be added implicitly; any microphone use requires an explicit permission/privacy design and its own runtime/hardware validation.

## Status and progress

This work is `ANDROID_SOURCE` only. It does not establish an AOSP build, Cuttlefish boot, physical camera compatibility, video quality, telephony/device support or beta readiness, and it grants no weighted project progress by itself.
