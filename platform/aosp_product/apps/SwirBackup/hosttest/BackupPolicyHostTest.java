package org.swir.phoneos.backup;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;

public final class BackupPolicyHostTest {
    private static final String ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static void rejects(Runnable action, String message) {
        boolean rejected = false;
        try { action.run(); }
        catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected, message);
    }

    public static void main(String[] args) {
        check(BackupPolicy.validEntryName("files/01-photo.jpg"), "safe entry");
        check(!BackupPolicy.validEntryName("../system"), "traversal rejected");
        check(!BackupPolicy.validEntryName("/absolute"), "absolute rejected");
        check(!BackupPolicy.validEntryName("files\\evil"), "backslash rejected");
        check("notes.txt".equals(BackupPolicy.safeDisplayName("notes.txt")), "display name");
        check("document".equals(BackupPolicy.safeDisplayName("..")), "dot-dot display name rejected");
        check(!BackupPolicy.safeEntryName("photo.jpg", 0).isEmpty(), "entry build");
        check(BackupPolicy.safeEntryName("photo.jpg", BackupPolicy.MAX_FILES).isEmpty(), "count bound");
        check(BackupPolicy.sizeAllowed(1024, 2048), "size bound");
        check(!BackupPolicy.sizeAllowed(BackupPolicy.MAX_ENTRY_BYTES + 1, 2048), "entry too large");
        check(BackupPolicy.backupFileName(1234).endsWith(".swirbackup"), "extension");
        check(BackupPolicy.validSha256(ABC_SHA256), "canonical sha256");
        check(!BackupPolicy.validSha256(ABC_SHA256.toUpperCase()), "uppercase digest rejected");

        BackupPolicy.FileRecord first = new BackupPolicy.FileRecord(
                "files/01-notes.txt", "notes.txt", 3, ABC_SHA256);
        BackupPolicy.Manifest manifest = BackupPolicy.manifest(
                "swir/test/device:17/build:userdebug/test-keys", 35, Collections.singletonList(first));
        String encoded = BackupPolicy.encodeManifest(manifest);
        check(encoded.startsWith("schema=2\n"), "schema 2 emitted");
        BackupPolicy.Manifest parsed = BackupPolicy.parseManifest(encoded);
        check(parsed.files.size() == 1, "manifest file count");
        check("notes.txt".equals(parsed.files.get(0).displayName), "manifest display name round trip");
        check(ABC_SHA256.equals(parsed.files.get(0).sha256), "manifest digest round trip");
        check(BackupPolicy.encodeManifest(parsed).equals(encoded), "manifest canonical round trip");

        String duplicate = encoded.replace("schema=2\n", "schema=2\nschema=2\n");
        rejects(() -> BackupPolicy.parseManifest(duplicate), "duplicate key rejected");
        rejects(() -> BackupPolicy.parseManifest(encoded.replace("schema=2", "schema=1")), "legacy schema not accepted as v2");
        check(BackupPolicy.isLegacyManifest("schema=1\nbuild=x\nsdk=35\nfiles=0\n"), "legacy manifest recognized for inspect-only mode");
        rejects(() -> BackupPolicy.parseManifest(encoded.replace(ABC_SHA256, ABC_SHA256.toUpperCase())), "non-canonical digest rejected");
        rejects(() -> BackupPolicy.parseManifest(encoded.replace("files=1\n", "files=2\n")), "missing records rejected");
        rejects(() -> BackupPolicy.parseManifest(encoded + "extra=value\n"), "unknown keys rejected");

        BackupPolicy.FileRecord traversal = new BackupPolicy.FileRecord(
                "files/../notes.txt", "notes.txt", 3, ABC_SHA256);
        rejects(() -> BackupPolicy.manifest("build", 35, Collections.singletonList(traversal)), "manifest traversal rejected");
        BackupPolicy.FileRecord wrongIndex = new BackupPolicy.FileRecord(
                "files/02-notes.txt", "notes.txt", 3, ABC_SHA256);
        rejects(() -> BackupPolicy.manifest("build", 35, Collections.singletonList(wrongIndex)), "entry index binding enforced");
        BackupPolicy.FileRecord unsafeName = new BackupPolicy.FileRecord(
                "files/01-document", "..", 3, ABC_SHA256);
        rejects(() -> BackupPolicy.manifest("build", 35, Collections.singletonList(unsafeName)), "unsafe restore name rejected");

        ArrayList<BackupPolicy.FileRecord> oversized = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            oversized.add(new BackupPolicy.FileRecord(
                    BackupPolicy.safeEntryName("f" + i, i), "f" + i, BackupPolicy.MAX_ENTRY_BYTES, ABC_SHA256));
        }
        rejects(() -> BackupPolicy.manifest("build", 35, oversized), "aggregate size limit enforced");

        rejects(() -> BackupPolicy.manifest("", 35, Arrays.asList(first)), "empty build rejected");
        rejects(() -> BackupPolicy.manifest("build", 0, Arrays.asList(first)), "invalid sdk rejected");
    }
}
