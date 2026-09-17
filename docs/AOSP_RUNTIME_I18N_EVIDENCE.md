# AOSP Runtime Localization Evidence

SwirPhoneOS treats localization as a runtime property, not only a source-file property. Source lint proves catalog structure and checked-in Android resources; it does **not** prove that Android applies those resources correctly after boot.

This evidence path is deliberately Cuttlefish-only and fail-closed. It must never be reused as physical-device compatibility evidence.

## Source LocaleConfig gate

Every source-ready first-party app now declares `android:localeConfig="@xml/locales_config"` and ships a package-local `res/xml/locales_config.xml` containing exactly the shared EN/PL/NB/DE/ES/FR/PT/AR catalog. `python -m swirphoneos.android_locale_config` validates the manifest declaration, exact locale set/order, `supportsRtl=true`, and exact AOSP staging coverage for every source-ready package. This is source evidence only.

Android's per-app language surface depends on an application LocaleConfig. Keeping that metadata data-driven and staged with the app prevents the runtime locale test from relying on an undeclared or stale supported-language list.

## Runtime locale matrix

After the exact pinned SwirPhoneOS Cuttlefish product has passed `cuttlefish-evidence` and the ordinary package launch smoke, run:

```sh
python -m swirphoneos.cuttlefish_i18n \
  --adb /absolute/path/to/trusted/adb \
  --manifest system_apps/manifest.json \
  > runtime-i18n-evidence.json
```

The collector:

- requires one exact local emulator/Cuttlefish transport and rejects physical/network device serials;
- requires complete SwirPhoneOS runtime identity before changing any locale;
- captures the current Android user and every source-ready app's original per-app locale override;
- exercises every checked-in shared locale for every source-ready package using Android's `cmd locale set-app-locales` / `get-app-locales` interface;
- resolves and launches only package-local launcher activities;
- requires successful `am start -W` and resumed-foreground confirmation for every package/locale pair;
- records which checked-in locales are RTL;
- restores every captured app locale override exactly before accepting evidence.

If a test fails, restoration is still attempted. If restoration itself cannot be verified, the evidence run fails and the disposable Cuttlefish guest must be reset/discarded before another evidence attempt.

The allowlist does not expose package installation, arbitrary shell, system setting mutation, root, reboot, flash, erase, physical-device operations or registry promotion.

## Bound runtime review

Bind the exact boot, launch and locale-matrix reports:

```sh
python -m swirphoneos.runtime_review_evidence \
  --runtime runtime-evidence.json \
  --smoke app-smoke-evidence.json \
  --i18n runtime-i18n-evidence.json \
  --manifest system_apps/manifest.json \
  > runtime-review-evidence.json
```

The binder requires:

- the same exact SwirPhoneOS build fingerprint in all reports;
- the exact current source-ready package set from `system_apps/manifest.json`;
- the exact current shared locale set and order;
- one successful launch result for every package;
- one successful locale result for every package × locale pair;
- verified restoration of all captured locale overrides;
- fail-closed safety flags and no status-promotion claim.

It hashes the raw input reports and the current app manifest so reports from different runs or repository states cannot be silently mixed.

## What this proves

Successful evidence proves, for one exact Cuttlefish build:

- Android boot identity was complete;
- all source-ready apps were installed and launchable;
- Android accepted and reported each checked-in per-app locale override;
- every app could be launched while each locale override was active;
- every captured original app-locale override was restored.

## What this does not prove

The report intentionally keeps these claims false:

- visual RTL mirroring verified;
- accessibility review complete;
- visual translation review complete;
- physical-device support;
- app status promotion;
- device writes authorized.

Focused interactive review is still required for text expansion/clipping, Arabic RTL mirroring, fonts/scripts, input methods, locale-specific number/date/time/unit formatting, TalkBack/accessibility semantics, color/contrast, touch targets and feature-specific behavior. Hardware-dependent apps still require exact-device evidence.

Runtime localization evidence therefore strengthens the future `ANDROID_RUNTIME` review gate but does not complete it by itself and does not increase the weighted project percentage.
