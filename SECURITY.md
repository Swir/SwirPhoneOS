# Security and safety

This foundation has no phone-write capability. Offline property reports are not authentication or permission to flash. Reject missing/ambiguous identity, unsupported firmware/layout, unknown bootloader state, untrusted images and untested recovery before any future destructive operation.

Never publish serial numbers, IMEI, unlock tokens, account credentials or signing keys. Never bypass OEM/account restrictions. Do not automatically unlock, erase, flash, relock or disable Verified Boot. Owner confirmation and exact-device validation are mandatory for write workflows. No universal full-backup or guaranteed unbricking claim is permitted.

Keep release keys outside source control. Authenticate artifacts and metadata, not just their transport; a SHA-256 digest alone is not a trusted signature. Review upstream/component licenses before redistribution. No blanket license is granted over third-party components; the original-code license policy must be finalized before the first distributed binary.

CI actions are pinned to reviewed full commit SHAs with read-only permissions and no publication step. See [GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

A private vulnerability-reporting contact/process must be established before public binary distribution. Do not post exploit details or private phone data in a public issue.
