package org.swir.phoneos.browser;

public final class BrowserPolicyHostTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check("https://example.com".equals(BrowserPolicy.normalizeUrl("example.com")), "https default");
        check(BrowserPolicy.isSafeUrl("https://example.com/path"), "https accepted");
        check(!BrowserPolicy.isSafeUrl("http://example.com"), "cleartext rejected");
        check(!BrowserPolicy.isSafeUrl("file:///etc/passwd"), "file rejected");
        check(!BrowserPolicy.isSafeUrl("https://user@example.com"), "userinfo rejected");
        check("example.com".equals(BrowserPolicy.displayHost("https://example.com/a")), "host");
        check(BrowserPolicy.searchUrl("swir phone os").startsWith("https://duckduckgo.com/?q="), "search url");
        check(BrowserPolicy.searchUrl("   ").isEmpty(), "blank query rejected");
    }
}
