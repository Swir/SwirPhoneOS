package org.swir.phoneos.settings;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** Permission-free routes into authoritative Android settings surfaces. */
public final class SettingsCatalog {
    public static final class Entry {
        private final String id;
        private final String action;
        private final String keywords;

        Entry(String id, String action, String keywords) {
            this.id = id;
            this.action = action;
            this.keywords = keywords;
        }

        public String id() { return id; }
        public String action() { return action; }
        String keywords() { return keywords; }
    }

    private static final List<Entry> ENTRIES = Collections.unmodifiableList(Arrays.asList(
            new Entry("wifi", "android.settings.WIFI_SETTINGS", "wifi wlan internet network"),
            new Entry("bluetooth", "android.settings.BLUETOOTH_SETTINGS", "bluetooth devices nearby"),
            new Entry("display", "android.settings.DISPLAY_SETTINGS", "display screen brightness dark theme"),
            new Entry("sound", "android.settings.SOUND_SETTINGS", "sound volume vibration audio"),
            new Entry("security", "android.settings.SECURITY_SETTINGS", "security lock biometrics credentials"),
            new Entry("privacy", "android.settings.PRIVACY_SETTINGS", "privacy permissions sensors"),
            new Entry("accessibility", "android.settings.ACCESSIBILITY_SETTINGS", "accessibility vision hearing interaction"),
            new Entry("language_region", "android.settings.LOCALE_SETTINGS", "language locale region keyboard"),
            new Entry("storage", "android.settings.INTERNAL_STORAGE_SETTINGS", "storage disk files space"),
            new Entry("apps", "android.settings.APPLICATION_SETTINGS", "apps applications packages permissions")
    ));

    private SettingsCatalog() {}

    public static List<Entry> entries() {
        return ENTRIES;
    }

    public static boolean matches(Entry entry, String query) {
        if (query == null || query.trim().isEmpty()) return true;
        String needle = query.trim().toLowerCase(Locale.ROOT);
        return entry.id().toLowerCase(Locale.ROOT).contains(needle)
                || entry.keywords().toLowerCase(Locale.ROOT).contains(needle);
    }
}
