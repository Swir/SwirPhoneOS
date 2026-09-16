package org.swir.phoneos.privacy;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** Reviewed permission-free routes into authoritative Android privacy surfaces. */
public final class PrivacyCatalog {
    public static final class Entry {
        private final String id;
        private final String action;
        Entry(String id, String action) { this.id = id; this.action = action; }
        public String id() { return id; }
        public String action() { return action; }
    }

    private static final List<Entry> ENTRIES;
    static {
        List<Entry> entries = new ArrayList<>();
        entries.add(new Entry("privacy", "android.settings.PRIVACY_SETTINGS"));
        entries.add(new Entry("permissions", "android.settings.MANAGE_PERMISSIONS"));
        entries.add(new Entry("location", "android.settings.LOCATION_SOURCE_SETTINGS"));
        entries.add(new Entry("apps", "android.settings.APPLICATION_SETTINGS"));
        entries.add(new Entry("special_access", "android.settings.MANAGE_SPECIAL_APP_ACCESSES"));
        ENTRIES = Collections.unmodifiableList(entries);
    }

    private PrivacyCatalog() {}

    public static List<Entry> entries() { return ENTRIES; }

    public static List<Entry> search(String query) {
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (needle.isEmpty()) return ENTRIES;
        List<Entry> found = new ArrayList<>();
        for (Entry entry : ENTRIES) {
            if (entry.id.contains(needle) || entry.action.toLowerCase(Locale.ROOT).contains(needle)) found.add(entry);
        }
        return found;
    }
}
