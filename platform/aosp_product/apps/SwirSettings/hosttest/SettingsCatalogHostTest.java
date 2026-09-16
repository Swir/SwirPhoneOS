package org.swir.phoneos.settings;

import java.util.HashSet;
import java.util.Set;

public final class SettingsCatalogHostTest {
    public static void main(String[] args) {
        if (SettingsCatalog.entries().size() != 10) throw new AssertionError("expected 10 routes");
        Set<String> ids = new HashSet<>();
        Set<String> actions = new HashSet<>();
        for (SettingsCatalog.Entry entry : SettingsCatalog.entries()) {
            if (!ids.add(entry.id())) throw new AssertionError("duplicate id: " + entry.id());
            if (!actions.add(entry.action())) throw new AssertionError("duplicate action: " + entry.action());
            if (!entry.action().startsWith("android.settings.")) throw new AssertionError("unsafe action namespace");
        }
        if (!SettingsCatalog.matches(SettingsCatalog.entries().get(0), "network")) {
            throw new AssertionError("wifi search keyword missing");
        }
        if (SettingsCatalog.matches(SettingsCatalog.entries().get(0), "camera")) {
            throw new AssertionError("unrelated search matched");
        }
    }
}
