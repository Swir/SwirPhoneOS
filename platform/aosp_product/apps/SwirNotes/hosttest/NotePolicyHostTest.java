package org.swir.phoneos.notes;

public final class NotePolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(NotePolicy.validNote("Roadmap", "Build Cuttlefish"), "valid note rejected");
        check(!NotePolicy.validNote("", "   "), "empty note accepted");
        check(NotePolicy.matches("CUTTLE", "Roadmap", "Build Cuttlefish"), "search mismatch");
        check(!NotePolicy.matches("camera", "Roadmap", "Build Cuttlefish"), "false search hit");
        check("Project_name".equals(NotePolicy.safeExportBase(" Project/name ")), "unsafe export name");
        check(NotePolicy.exportMarkdown("Title", "Body").equals("# Title\n\nBody\n"), "markdown export drift");
        check(NotePolicy.normalizedTitle(null).isEmpty(), "null title normalization failed");
    }
}
