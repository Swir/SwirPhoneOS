package org.swir.phoneos.privacy;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/** Pure-Java bounds/sanitization policy for the first-Beta permission review surface. */
public final class PermissionReviewPolicy {
    public static final int MAX_PACKAGES = 7;
    public static final int MAX_PERMISSIONS_PER_PACKAGE = 32;
    private static final int MAX_LABEL_CODEPOINTS = 72;

    private static final List<String> BETA_SURFACE_PACKAGES = Collections.unmodifiableList(
            java.util.Arrays.asList(
                    "org.swir.phoneos.launcher",
                    "org.swir.phoneos.settings",
                    "org.swir.phoneos.files",
                    "org.swir.phoneos.update",
                    "org.swir.phoneos.privacy",
                    "org.swir.phoneos.device_care",
                    "org.swir.phoneos.swirroot"));

    private PermissionReviewPolicy() {}

    public static List<String> betaSurfacePackages() {
        return BETA_SURFACE_PACKAGES;
    }

    public static String normalizeLabel(CharSequence raw) {
        if (raw == null) return "";
        StringBuilder out = new StringBuilder();
        boolean pendingSpace = false;
        for (int index = 0; index < raw.length();) {
            int codePoint = Character.codePointAt(raw, index);
            index += Character.charCount(codePoint);
            if (Character.isISOControl(codePoint)) continue;
            if (Character.isWhitespace(codePoint)) {
                pendingSpace = out.length() > 0;
                continue;
            }
            if (pendingSpace) {
                out.append(' ');
                pendingSpace = false;
            }
            if (out.codePointCount(0, out.length()) >= MAX_LABEL_CODEPOINTS) break;
            out.appendCodePoint(codePoint);
        }
        return out.toString().trim();
    }

    public static String shortPermissionName(String permission) {
        if (permission == null) return "";
        String value = permission.trim();
        if (value.isEmpty() || value.length() > 180) return "";
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            boolean ok = Character.isLetterOrDigit(ch) || ch == '.' || ch == '_';
            if (!ok) return "";
        }
        int dot = value.lastIndexOf('.');
        return dot >= 0 && dot + 1 < value.length() ? value.substring(dot + 1) : value;
    }

    public static List<String> boundedPermissions(String[] permissions) {
        if (permissions == null || permissions.length == 0) return Collections.emptyList();
        Set<String> unique = new LinkedHashSet<>();
        for (String permission : permissions) {
            if (unique.size() >= MAX_PERMISSIONS_PER_PACKAGE) break;
            if (shortPermissionName(permission).isEmpty()) continue;
            unique.add(permission);
        }
        List<String> result = new ArrayList<>(unique);
        Collections.sort(result);
        return Collections.unmodifiableList(result);
    }

    public static boolean matches(String query, String appLabel, List<String> permissions) {
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (needle.isEmpty()) return true;
        if (normalizeLabel(appLabel).toLowerCase(Locale.ROOT).contains(needle)) return true;
        for (String permission : permissions) {
            if (permission.toLowerCase(Locale.ROOT).contains(needle)
                    || shortPermissionName(permission).toLowerCase(Locale.ROOT).contains(needle)) {
                return true;
            }
        }
        return false;
    }
}
