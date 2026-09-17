package org.swir.phoneos.browser;

public final class BrowserPolicyHostTest {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        require(BrowserPolicy.normalizeAddress(null).equals("about:blank"), "null must stay local");
        require(BrowserPolicy.normalizeAddress("example.com").equals("https://example.com"), "host must prefer HTTPS");
        require(BrowserPolicy.normalizeAddress("  https://example.com/a  ").equals("https://example.com/a"), "URL must trim");
        require(BrowserPolicy.normalizeAddress("private search").startsWith("https://duckduckgo.com/?q="), "plain text must become explicit search");
        require(BrowserPolicy.isAllowedUri("https://example.com"), "HTTPS must be allowed");
        require(BrowserPolicy.isAllowedUri("http://example.com"), "HTTP navigation may be represented even though cleartext is disabled by manifest");
        require(!BrowserPolicy.isAllowedUri("file:///sdcard/test"), "file URI must be blocked");
        require(!BrowserPolicy.isAllowedUri("javascript:alert(1)"), "javascript URI must be blocked");
        require(!BrowserPolicy.isAllowedUri("intent://example"), "intent URI must be blocked");
        require(!BrowserPolicy.canShare("about:blank"), "local blank page is not shareable");
        require(BrowserPolicy.canShare("https://example.com"), "HTTPS page is shareable");
    }
}
