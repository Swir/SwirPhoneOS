package org.swir.phoneos.apps;

public final class AppCatalogPolicyHostTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(AppCatalogPolicy.matches("Swir Files", "org.swir.phoneos.files", "files"), "label search");
        check(AppCatalogPolicy.matches("Swir Files", "org.swir.phoneos.files", "phoneos"), "package search");
        check(AppCatalogPolicy.validPackageName("org.swir.phoneos.files"), "package validation");
        check(!AppCatalogPolicy.validPackageName("../bad"), "bad package rejected");
        String digest = AppCatalogPolicy.sha256(new byte[]{1, 2, 3});
        check(digest.length() == 64 && AppCatalogPolicy.shortDigest(digest).length() == 16, "signature digest");
        check("".equals(AppCatalogPolicy.shortDigest("bad")), "bad digest rejected");
        check(AppCatalogPolicy.updateSource(true, "com.example.installer") == AppCatalogPolicy.UpdateSource.SYSTEM_IMAGE, "system image wins");
        check(AppCatalogPolicy.updateSource(false, "com.example.installer") == AppCatalogPolicy.UpdateSource.EXTERNAL_INSTALLER, "external installer");
        check(AppCatalogPolicy.updateSource(false, "../bad") == AppCatalogPolicy.UpdateSource.LOCAL_UNKNOWN, "bad installer rejected");
        check(AppCatalogPolicy.updateSource(false, null) == AppCatalogPolicy.UpdateSource.LOCAL_UNKNOWN, "missing installer");
        check(AppCatalogPolicy.normalizeUpdateTime(1234L) == 1234L, "valid update time");
        check(AppCatalogPolicy.normalizeUpdateTime(0L) == 0L, "zero update time");
        check(AppCatalogPolicy.normalizeUpdateTime(-1L) == 0L, "negative update time");
    }
}
