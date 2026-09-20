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
        check("Swir Files".equals(AppCatalogPolicy.normalizeLabel("  Swir\n\u0000Files  ")), "label controls collapsed");
        StringBuilder longLabel = new StringBuilder();
        for (int i = 0; i < AppCatalogPolicy.MAX_LABEL + 20; i++) longLabel.append('x');
        check(AppCatalogPolicy.normalizeLabel(longLabel.toString()).length() == AppCatalogPolicy.MAX_LABEL, "label bound");
        check("1.2.3 beta".equals(AppCatalogPolicy.normalizeVersion("  1.2.3\tbeta ", 7L)), "version normalized");
        check("42".equals(AppCatalogPolicy.normalizeVersion("\n\u0000", 42L)), "version fallback");
        check("0".equals(AppCatalogPolicy.normalizeVersion(null, -1L)), "negative version fallback bounded");
        check(AppCatalogPolicy.catalogCapacityAvailable(0), "catalog starts available");
        check(AppCatalogPolicy.catalogCapacityAvailable(AppCatalogPolicy.MAX_CATALOG_APPS - 1), "catalog last slot available");
        check(!AppCatalogPolicy.catalogCapacityAvailable(AppCatalogPolicy.MAX_CATALOG_APPS), "catalog hard limit");
        check(!AppCatalogPolicy.catalogCapacityAvailable(-1), "negative catalog count rejected");
        String digest = AppCatalogPolicy.sha256(new byte[]{1, 2, 3});
        check(digest.length() == 64 && AppCatalogPolicy.shortDigest(digest).length() == 16, "signature digest");
        check("".equals(AppCatalogPolicy.shortDigest("bad")), "bad digest rejected");
        check(AppCatalogPolicy.updateSource(true, "com.example.installer") == AppCatalogPolicy.UpdateSource.SYSTEM_IMAGE, "system image wins");
        check(AppCatalogPolicy.updateSource(false, "com.example.installer") == AppCatalogPolicy.UpdateSource.EXTERNAL_INSTALLER, "external installer");
        check(AppCatalogPolicy.updateSource(false, "../bad") == AppCatalogPolicy.UpdateSource.LOCAL_UNKNOWN, "bad installer rejected");
        check(AppCatalogPolicy.updateSource(false, null) == AppCatalogPolicy.UpdateSource.LOCAL_UNKNOWN, "missing installer");
        check(AppCatalogPolicy.updateState(true, false, null) == AppCatalogPolicy.UpdateState.SYSTEM_BASELINE, "system baseline state");
        check(AppCatalogPolicy.updateState(true, true, null) == AppCatalogPolicy.UpdateState.SYSTEM_UPDATED, "updated system app state");
        check(AppCatalogPolicy.updateState(false, true, null) == AppCatalogPolicy.UpdateState.SYSTEM_UPDATED, "updated-system flag wins");
        check(AppCatalogPolicy.updateState(false, false, "com.example.installer") == AppCatalogPolicy.UpdateState.EXTERNAL_MANAGED, "external managed state");
        check(AppCatalogPolicy.updateState(false, false, "../bad") == AppCatalogPolicy.UpdateState.LOCAL_UNKNOWN, "bad installer update state rejected");
        check(AppCatalogPolicy.updateState(false, false, null) == AppCatalogPolicy.UpdateState.LOCAL_UNKNOWN, "unknown update state");
        check(AppCatalogPolicy.normalizeUpdateTime(1234L) == 1234L, "valid update time");
        check(AppCatalogPolicy.normalizeUpdateTime(0L) == 0L, "zero update time");
        check(AppCatalogPolicy.normalizeUpdateTime(-1L) == 0L, "negative update time");
    }
}
