# Security and Safety Policy

This foundation is not approved for installing an OS on a phone. The current CLI has no write commands. ADB-reported properties are untrusted hints; an unlocked/Treble-capable report never authorizes flashing.

The owner must obtain Platform Tools from a trusted Android SDK installation and provide its absolute executable path. Filename/path checks are not binary authenticity verification. The adapter suppresses raw errors, avoids requesting serial/IMEI properties, limits allowed commands and removes inherited ADB server/selection environment settings. ADB can still start a local host server. No network download, backup or device write is implemented. USB ADB must already be enabled and authorized by the owner.

Before any future destructive capability, require verified device identity, firmware and partition map; expected USB/boot mode; signed artifacts; interactive confirmation; a durable transaction journal; and tested recovery. Bootloader unlock can erase data. Encrypted/protected data cannot be universally backed up. Never automatically disable Verified Boot, bypass account/OEM security, relock a custom system or downgrade across anti-rollback limits.

Release/update signing keys and credentials must never enter source control, logs or generated archives. Public release images must not rely on publicly known AOSP test keys. Verify redistribution rights for vendor components. SHA-256 without an authenticated trust root is not sufficient download authenticity.

A dedicated private vulnerability-reporting process is pending before binary distribution. Until then, do not publish secrets, exploitable private details or identifying device logs in public issues. Record this gap rather than inventing a reporting address. See `docs/SOURCES.md` for upstream references.
