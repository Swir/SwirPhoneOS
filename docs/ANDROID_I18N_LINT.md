# Android localization source lint

SwirPhoneOS treats localization as a build-quality contract rather than a late translation pass. The checked-in Android applications use English as the canonical source locale and must remain compatible with every locale present in the shared host localization registry.

The Android localization lint is intentionally **source-only evidence**. Passing it does not mean an APK was built, that locale switching works at runtime, that Arabic/RTL was visually reviewed, or that a physical device was verified. Those claims remain behind the AOSP runtime and hardware gates.

## Enforced source contract

For every application currently marked `ANDROID_SOURCE`, the lint discovers the application by its manifest package rather than trusting a folder name. It then requires a readable, regular `strings.xml` catalog for every shared locale. Simple language tags use normal Android `values-<language>` directories; future BCP-47 tags can use Android's `values-b+...` qualifier without changing the lint logic.

The lint verifies:

- exact string-resource key coverage against canonical English;
- exact plural-resource name coverage while allowing locale-specific plural quantity sets;
- a mandatory `other` quantity for every plural resource;
- only Android plural quantities `zero`, `one`, `two`, `few`, `many`, and `other`;
- Java/Android formatter argument identity and type across translations, including indexed placeholders such as `%1$s` and `%2$d`;
- all production Java files for direct non-empty user-facing literals passed to common UI sinks such as `setText`, `setTitle`, `setHint`, dialog button/message methods, content descriptions, and `Toast.makeText`;
- comments are removed before UI-literal scanning so documentation examples do not create false failures;
- no runtime, hardware, write, flash, root, or beta-readiness claim is produced by the lint.

Plural categories intentionally do **not** need to match English one-for-one. Arabic, for example, can provide `zero`, `two`, `few`, or `many` entries even when English has only `one` and `other`. Every translated quantity must preserve the formatter arguments required by the corresponding English quantity, falling back to English `other` when that quantity is not present in the source catalog.

## Why formatter parity is fail-closed

A translated resource can have all the correct keys and still crash or display incorrect data if a translator changes `%1$d` into `%1$s`, duplicates an argument index, or drops a required placeholder. The lint therefore validates formatter signatures in addition to resource-key parity.

This validation is separate from host-tool localization, which uses named Python format fields. Both contracts use English as the source and both are enforced by the normal host unit-test workflow.

## CI coverage

`tests/test_android_i18n.py` runs under the existing cross-platform unit-test matrix. It checks the repository state and negative regressions for:

- placeholder type drift;
- placeholder index drift;
- direct executable Java UI literals;
- comments containing UI examples;
- missing translated keys;
- locale-specific plural categories with valid argument contracts;
- plural resources missing the mandatory `other` quantity.

Because the normal `Host checks` workflow already executes `python -m unittest discover -s tests -v` on Ubuntu and Windows for Python 3.11 through 3.14, adding or changing an `ANDROID_SOURCE` app can no longer silently bypass these localization checks.

## Runtime work still required

Before any application can be promoted to `ANDROID_RUNTIME`, the pinned SwirPhoneOS AOSP product must build and boot, every source-ready package must pass emulator launch smoke, and focused interactive checks must cover locale changes, text expansion, accessibility, truncation, bidirectional content, Arabic RTL mirroring, locale-specific date/time/number rendering, and permission/system-dialog behavior.

The project-wide weighted progress therefore remains unchanged by this source lint alone.
