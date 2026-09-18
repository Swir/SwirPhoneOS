package org.swir.phoneos.browser;

public final class BrowserPolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check("https://example.com".equals(BrowserPolicy.normalizeUrl("example.com")), "host should default to HTTPS");
        check(BrowserPolicy.isSafeUrl("https://example.com/path?q=1"), "HTTPS URL should be accepted");
        check(!BrowserPolicy.isSafeUrl("http://example.com"), "HTTP must be rejected");
        check(!BrowserPolicy.isSafeUrl("file:///tmp/demo"), "file URLs must be rejected");
        check(BrowserPolicy.normalizeUrl("https://user:pass@example.com").isEmpty(), "userinfo must be rejected");
        check("example.com".equals(BrowserPolicy.displayHost("https://example.com/a")), "host display mismatch");
        check(BrowserPolicy.searchUrl("swir phone").startsWith("https://duckduckgo.com/?q="), "search must preserve the reviewed HTTPS provider");
        check(BrowserPolicy.searchUrl("   ").isEmpty(), "blank search must fail closed");

        check(BrowserPolicy.isSafeDownloadUrl("https://example.com/file.zip"), "explicit HTTPS download should be accepted");
        check(!BrowserPolicy.isSafeDownloadUrl("example.com/file.zip"), "scheme-less download must be rejected");
        check(!BrowserPolicy.isSafeDownloadUrl("http://example.com/file.zip"), "HTTP download must be rejected");
        check(!BrowserPolicy.isSafeDownloadUrl("file:///tmp/file.zip"), "file download must be rejected");
        check(!BrowserPolicy.isSafeDownloadUrl("data:text/plain,hello"), "data download must be rejected");
        check(!BrowserPolicy.isSafeDownloadUrl("javascript:alert(1)"), "javascript download must be rejected");

        check("report_.._secret_.pdf".equals(BrowserPolicy.safeDownloadFileName("report/../secret?.pdf")), "reserved filename characters must be sanitized");
        check("download.bin".equals(BrowserPolicy.safeDownloadFileName("...")), "dot-only filename must fall back");
        check("download.bin".equals(BrowserPolicy.safeDownloadFileName("  ")), "blank filename must fall back");
        String longName = BrowserPolicy.safeDownloadFileName("a".repeat(200) + ".zip");
        check(longName.length() <= BrowserPolicy.MAX_DOWNLOAD_FILENAME_LENGTH, "filename must be bounded");
        check(longName.endsWith(".zip"), "short extension should be preserved when truncating");

        check("application/pdf".equals(BrowserPolicy.safeMimeType(" Application/PDF ")), "MIME should normalize safely");
        check("application/vnd.swir+json".equals(BrowserPolicy.safeMimeType("application/vnd.swir+json")), "structured MIME should be allowed");
        check(BrowserPolicy.safeMimeType("text/plain; charset=utf-8").isEmpty(), "parameterized MIME must be rejected at this boundary");
        check(BrowserPolicy.safeMimeType("text").isEmpty(), "MIME without slash must be rejected");
        check(BrowserPolicy.safeMimeType("text/plain\nX-Bad: 1").isEmpty(), "control characters must be rejected");
    }
}
