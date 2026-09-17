package org.swir.phoneos.backup;

public final class BackupPolicyHostTest {
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    public static void main(String[] args) {
        check(BackupPolicy.validEntryName("files/01-photo.jpg"), "safe entry");
        check(!BackupPolicy.validEntryName("../system"), "traversal rejected");
        check(!BackupPolicy.validEntryName("/absolute"), "absolute rejected");
        check(!BackupPolicy.validEntryName("files\\evil"), "backslash rejected");
        check("notes.txt".equals(BackupPolicy.safeDisplayName("notes.txt")), "display name");
        check(!BackupPolicy.safeEntryName("photo.jpg", 0).isEmpty(), "entry build");
        check(BackupPolicy.safeEntryName("photo.jpg", BackupPolicy.MAX_FILES).isEmpty(), "count bound");
        check(BackupPolicy.sizeAllowed(1024, 2048), "size bound");
        check(!BackupPolicy.sizeAllowed(BackupPolicy.MAX_ENTRY_BYTES + 1, 2048), "entry too large");
        check(BackupPolicy.backupFileName(1234).endsWith(".swirbackup"), "extension");
    }
}
