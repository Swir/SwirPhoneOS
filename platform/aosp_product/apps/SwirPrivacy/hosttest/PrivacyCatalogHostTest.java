package org.swir.phoneos.privacy;

import java.util.HashSet;
import java.util.Set;

public final class PrivacyCatalogHostTest {
    public static void main(String[] args) {
        check(PrivacyCatalog.entries().size() == 5, "route count");
        Set<String> actions = new HashSet<>();
        for (PrivacyCatalog.Entry entry : PrivacyCatalog.entries()) {
            check(entry.action().startsWith("android.settings."), "settings namespace");
            check(actions.add(entry.action()), "unique action");
        }
        check(PrivacyCatalog.search("permission").size() == 1, "permission search");
        check(PrivacyCatalog.search("").size() == 5, "empty search");
        check(PrivacyCatalog.search("missing").isEmpty(), "missing search");
    }

    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }
}
