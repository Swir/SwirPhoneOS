package org.swir.phoneos.launcher;

/** Pure-Java bounds used by the beta-core launcher and first-run setup surface. */
public final class LauncherPolicy {
    public static final int MAX_LABEL_CODEPOINTS = 80;
    public static final String REVIEW_LANGUAGE = "language";
    public static final String REVIEW_PRIVACY = "privacy";
    public static final String REVIEW_SECURITY = "security";

    private LauncherPolicy() {}

    public static String normalizeLabel(String value) {
        if (value == null) {
            return "";
        }
        StringBuilder out = new StringBuilder();
        boolean previousSpace = false;
        for (int i = 0; i < value.length();) {
            int cp = value.codePointAt(i);
            i += Character.charCount(cp);
            if (Character.isISOControl(cp)) {
                cp = ' ';
            }
            if (Character.isWhitespace(cp)) {
                if (previousSpace) {
                    continue;
                }
                cp = ' ';
                previousSpace = true;
            } else {
                previousSpace = false;
            }
            if (out.codePointCount(0, out.length()) >= MAX_LABEL_CODEPOINTS) {
                break;
            }
            out.appendCodePoint(cp);
        }
        return out.toString().trim();
    }

    public static boolean showPackage(String ownPackage, String packageName) {
        return packageName != null && !packageName.isEmpty() && !packageName.equals(ownPackage);
    }

    public static boolean isKnownReview(String review) {
        return REVIEW_LANGUAGE.equals(review)
                || REVIEW_PRIVACY.equals(review)
                || REVIEW_SECURITY.equals(review);
    }

    public static boolean setupReady(
            boolean languageReviewed,
            boolean privacyReviewed,
            boolean securityReviewed,
            boolean deviceSecure) {
        return languageReviewed && privacyReviewed && securityReviewed && deviceSecure;
    }
}
