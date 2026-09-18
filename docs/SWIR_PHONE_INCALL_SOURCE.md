# Swir Phone default-role and in-call source contract

Swir Phone now contains a first-party **source-stage** Android default-phone/in-call foundation while preserving the existing owner-visible `ACTION_DIAL` hand-off for outgoing call placement.

## What is implemented in source

`MainActivity` declares the standard `ACTION_DIAL` + `tel:` role-eligibility surface and exposes an explicit owner action that asks Android `RoleManager` for `ROLE_DIALER`. The request is never made automatically. The UI reports whether the role is currently held and only enables the active-call surface when Android reports that Swir Phone owns the role and the in-call service has an active call.

`SwirInCallService` is exported only through Android's `BIND_INCALL_SERVICE` service permission and declares `android.telecom.IN_CALL_SERVICE_UI=true`. When Android binds the service as the approved phone app, it keeps only the current in-process `Call` reference. Owner-visible controls can answer a ringing audio call, reject a ringing call or disconnect the active call. No call is placed from this service, no call log is read or written, and no call state is persisted.

Caller identity is shown only when Android reports `TelecomManager.PRESENTATION_ALLOWED`. Restricted, unknown, payphone or otherwise non-allowed presentations fail closed to the localized unknown-number label; the service checks presentation before reading the call handle so a private number is not exposed by this UI path.

`InCallActivity` is not exported. It presents the allowed active number and Android call state using localized resources and shared SwirPhoneOS design/touch tokens. Answer, reject and end-call actions are enabled only for compatible call states. The activity polls only the in-process service state and contains no network, storage, shell or provider I/O.

The service may request the in-call activity for ringing/dialing/connecting calls. Whether Android permits that launch, whether role eligibility is accepted, and how the exact telephony/IMS stack behaves are runtime properties and are not inferred from source.

## Permission and safety boundary

Swir Phone still declares **no `uses-permission` entries**. `BIND_INCALL_SERVICE` is a service binding permission enforced by Android, not a permission requested by Swir Phone. The implementation does not add `CALL_PHONE`, call-log access, SMS access, contacts access, storage, network or privileged process execution.

Outgoing calls continue to use `Intent.ACTION_DIAL`; the app does not use `Intent.ACTION_CALL` or `TelecomManager.placeCall`. This keeps call initiation owner-visible even when the default-phone role has not been verified yet.

The source contract deliberately does not implement recent-call history, multiple/conference-call orchestration, call recording, emergency-call policy, SIM/account selection policy, RTT/video calling, Bluetooth routing or carrier/IMS compatibility.

## Localization and verification

All owner-visible strings are resource-backed across the existing EN/PL/NB/DE/ES/FR/PT/AR catalogs. `tests/test_phone_incall_source.py` checks the manifest role/service boundary, explicit role request, no direct outgoing-call primitive, caller-presentation privacy gate, owner-visible call controls, staging closure and exact locale-key parity. The focused `SwirPhone source checks` workflow executes this contract alongside the existing Android source validator, localization checks and pure-Java dial policy.

## Truthful status

This is **source-stage implementation only**. Swir Phone remains `ANDROID_SOURCE`; `phone:in_call` and `phone:recent_calls` remain open in capability accounting until the pinned SwirPhoneOS image actually builds, Android accepts Swir Phone as the default phone app, incoming/outgoing call UI is exercised, and the exact physical telephony stack is validated. This work does not satisfy a beta gate, does not create supported-device evidence and does not increase weighted OS progress.
