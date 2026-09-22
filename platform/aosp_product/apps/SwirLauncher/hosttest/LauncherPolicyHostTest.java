package org.swir.phoneos.launcher;

public final class LauncherPolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    public static void main(String[] args) {
        check(LauncherPolicy.isKnownReview(LauncherPolicy.REVIEW_LANGUAGE), "language review must be known");
        check(LauncherPolicy.isKnownReview(LauncherPolicy.REVIEW_PRIVACY), "privacy review must be known");
        check(LauncherPolicy.isKnownReview(LauncherPolicy.REVIEW_SECURITY), "security review must be known");
        check(!LauncherPolicy.isKnownReview(""), "empty review must be rejected");
        check(!LauncherPolicy.isKnownReview("unknown"), "unknown review must be rejected");

        check(!LauncherPolicy.setupReady(false, false, false), "empty setup must stay blocked");
        check(!LauncherPolicy.setupReady(true, true, false), "security review is mandatory");
        check(!LauncherPolicy.setupReady(true, false, true), "privacy review is mandatory");
        check(!LauncherPolicy.setupReady(false, true, true), "language review is mandatory");
        check(LauncherPolicy.setupReady(true, true, true), "all setup reviews must unlock completion");

        check("Hello world".equals(LauncherPolicy.normalizeLabel("  Hello\n\tworld  ")), "labels must be normalized");
        check(LauncherPolicy.showPackage("org.swir.home", "org.swir.settings"), "other package must be visible");
        check(!LauncherPolicy.showPackage("org.swir.home", "org.swir.home"), "launcher must not list itself");
    }
}
