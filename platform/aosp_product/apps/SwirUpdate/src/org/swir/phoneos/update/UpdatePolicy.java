package org.swir.phoneos.update;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.Signature;
import java.util.Locale;

/** Pure-Java verification and channel policy used by Swir Update. */
public final class UpdatePolicy {
    public enum Channel { STABLE, BETA, DEVELOPER, UNKNOWN }

    public enum PackageState {
        REVIEW_READY_UNTRUSTED,
        REJECTED_NAME,
        REJECTED_SIZE,
        REJECTED_FORMAT,
        READ_FAILED
    }

    public enum ManifestState {
        AUTHENTIC_REVIEW_READY_NOT_STAGED,
        REJECTED_FORMAT,
        REJECTED_SIGNATURE,
        REJECTED_KEY_ID,
        REJECTED_SOURCE_BUILD,
        REJECTED_TARGET_BUILD,
        REJECTED_CHANNEL,
        REJECTED_PACKAGE_BINDING,
        REJECTED_ROLLBACK_POLICY
    }

    /** Hard read ceiling for owner-selected local OTA candidates. */
    public static final long MAX_PACKAGE_BYTES = 16L * 1024L * 1024L * 1024L;
    public static final int MAX_PACKAGE_NAME_CHARS = 180;
    public static final int MAX_MANIFEST_BYTES = 4096;
    public static final String MANIFEST_HEADER = "SWIR-OTA-MANIFEST-V1";

    public static final class PackageInspection {
        private final PackageState state;
        private final long sizeBytes;
        private final String sha256;

        PackageInspection(PackageState state, long sizeBytes, String sha256) {
            this.state = state;
            this.sizeBytes = sizeBytes;
            this.sha256 = sha256 == null ? "" : sha256;
        }

        public PackageState state() { return state; }
        public long sizeBytes() { return sizeBytes; }
        public String sha256() { return sha256; }
        public boolean reviewReady() { return state == PackageState.REVIEW_READY_UNTRUSTED; }
    }

    public static final class OtaManifest {
        private final String sourceFingerprint;
        private final String targetFingerprint;
        private final Channel channel;
        private final String packageName;
        private final long packageSize;
        private final String packageSha256;
        private final String keyId;
        private final boolean rollbackRequired;

        OtaManifest(
                String sourceFingerprint,
                String targetFingerprint,
                Channel channel,
                String packageName,
                long packageSize,
                String packageSha256,
                String keyId,
                boolean rollbackRequired) {
            this.sourceFingerprint = sourceFingerprint;
            this.targetFingerprint = targetFingerprint;
            this.channel = channel;
            this.packageName = packageName;
            this.packageSize = packageSize;
            this.packageSha256 = packageSha256;
            this.keyId = keyId;
            this.rollbackRequired = rollbackRequired;
        }

        public String sourceFingerprint() { return sourceFingerprint; }
        public String targetFingerprint() { return targetFingerprint; }
        public Channel channel() { return channel; }
        public String packageName() { return packageName; }
        public long packageSize() { return packageSize; }
        public String packageSha256() { return packageSha256; }
        public String keyId() { return keyId; }
        public boolean rollbackRequired() { return rollbackRequired; }
    }

    public static final class ManifestReview {
        private final ManifestState state;
        private final OtaManifest manifest;

        ManifestReview(ManifestState state, OtaManifest manifest) {
            this.state = state;
            this.manifest = manifest;
        }

        public ManifestState state() { return state; }
        public OtaManifest manifest() { return manifest; }
        public boolean authenticReviewReady() {
            return state == ManifestState.AUTHENTIC_REVIEW_READY_NOT_STAGED;
        }
        /** Source-stage trust review never authorizes staging, recovery handoff or device writes. */
        public boolean stagingAllowed() { return false; }
    }

    private UpdatePolicy() {}

    public static Channel channelForBuild(String type, String tags) {
        String safeType = type == null ? "" : type.trim().toLowerCase(Locale.ROOT);
        String safeTags = tags == null ? "" : tags.trim().toLowerCase(Locale.ROOT);
        if ("user".equals(safeType) && safeTags.contains("release-keys")) return Channel.STABLE;
        if ("userdebug".equals(safeType)) return Channel.BETA;
        if ("eng".equals(safeType)) return Channel.DEVELOPER;
        return Channel.UNKNOWN;
    }

    public static boolean fingerprintMatches(String expected, String actual) {
        return expected != null && actual != null && !expected.isEmpty() && expected.equals(actual);
    }

    public static boolean verifyDetachedSignature(byte[] metadata, byte[] signature, PublicKey key) {
        if (metadata == null || signature == null || key == null || metadata.length == 0 || signature.length == 0) return false;
        try {
            Signature verifier = Signature.getInstance("SHA256withRSA");
            verifier.initVerify(key);
            verifier.update(metadata);
            return verifier.verify(signature);
        } catch (Exception ignored) {
            return false;
        }
    }

    /**
     * Strictly parse the canonical detached-signature metadata format.
     * Fixed field order makes duplicate or ambiguous keys impossible and the exact UTF-8 bytes are
     * what the signature covers. No JSON normalization or permissive parser is involved.
     */
    public static OtaManifest parseCanonicalManifest(byte[] metadata) {
        if (metadata == null || metadata.length == 0 || metadata.length > MAX_MANIFEST_BYTES) return null;
        final String text;
        try {
            text = new String(metadata, StandardCharsets.UTF_8);
        } catch (Exception ignored) {
            return null;
        }
        if (text.indexOf('\r') >= 0 || text.indexOf('\0') >= 0) return null;
        String[] lines = text.split("\\n", -1);
        if (lines.length != 9 || !MANIFEST_HEADER.equals(lines[0])) return null;
        String source = exactField(lines[1], "source_fingerprint=", 1024);
        String target = exactField(lines[2], "target_fingerprint=", 1024);
        String channelValue = exactField(lines[3], "channel=", 16);
        String packageName = exactField(lines[4], "package_name=", MAX_PACKAGE_NAME_CHARS);
        String packageSizeValue = exactField(lines[5], "package_size=", 20);
        String packageSha256 = exactField(lines[6], "package_sha256=", 64);
        String keyId = exactField(lines[7], "key_id=", 128);
        String rollback = exactField(lines[8], "rollback_required=", 5);
        if (source == null || target == null || channelValue == null || packageName == null
                || packageSizeValue == null || packageSha256 == null || keyId == null || rollback == null) return null;
        if (!safePackageName(packageName) || !isLowerHexSha256(packageSha256)) return null;
        Channel channel;
        try {
            channel = Channel.valueOf(channelValue);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
        if (channel == Channel.UNKNOWN) return null;
        long packageSize;
        try {
            packageSize = Long.parseLong(packageSizeValue);
        } catch (NumberFormatException ignored) {
            return null;
        }
        if (packageSize <= 0L || packageSize > MAX_PACKAGE_BYTES) return null;
        if (!"true".equals(rollback) && !"false".equals(rollback)) return null;
        return new OtaManifest(
                source,
                target,
                channel,
                packageName,
                packageSize,
                packageSha256,
                keyId,
                "true".equals(rollback));
    }

    /**
     * Authenticate canonical metadata and bind it to the exact owner-selected package inspection.
     * A successful result remains review-only: no staging/recovery/device-write authorization exists.
     */
    public static ManifestReview reviewSignedManifest(
            byte[] metadata,
            byte[] signature,
            PublicKey trustedKey,
            String trustedKeyId,
            String currentFingerprint,
            Channel expectedChannel,
            String selectedPackageName,
            PackageInspection packageInspection) {
        OtaManifest manifest = parseCanonicalManifest(metadata);
        if (manifest == null) return new ManifestReview(ManifestState.REJECTED_FORMAT, null);
        if (!verifyDetachedSignature(metadata, signature, trustedKey)) {
            return new ManifestReview(ManifestState.REJECTED_SIGNATURE, manifest);
        }
        if (!safeSimpleValue(trustedKeyId, 128) || !manifest.keyId().equals(trustedKeyId)) {
            return new ManifestReview(ManifestState.REJECTED_KEY_ID, manifest);
        }
        if (!fingerprintMatches(manifest.sourceFingerprint(), currentFingerprint)) {
            return new ManifestReview(ManifestState.REJECTED_SOURCE_BUILD, manifest);
        }
        if (!safeSimpleValue(manifest.targetFingerprint(), 1024)) {
            return new ManifestReview(ManifestState.REJECTED_TARGET_BUILD, manifest);
        }
        if (expectedChannel == null || expectedChannel == Channel.UNKNOWN || manifest.channel() != expectedChannel) {
            return new ManifestReview(ManifestState.REJECTED_CHANNEL, manifest);
        }
        if (packageInspection == null || !packageInspection.reviewReady()
                || !manifest.packageName().equals(selectedPackageName)
                || manifest.packageSize() != packageInspection.sizeBytes()
                || !manifest.packageSha256().equals(packageInspection.sha256())) {
            return new ManifestReview(ManifestState.REJECTED_PACKAGE_BINDING, manifest);
        }
        if (!manifest.rollbackRequired()) {
            return new ManifestReview(ManifestState.REJECTED_ROLLBACK_POLICY, manifest);
        }
        return new ManifestReview(ManifestState.AUTHENTIC_REVIEW_READY_NOT_STAGED, manifest);
    }

    /**
     * Read-only preflight for an owner-selected local OTA candidate.
     *
     * This intentionally proves only local byte identity: simple .zip name, bounded/read-consistent
     * size, ZIP local-file header and SHA-256. It does not authenticate metadata, establish target
     * compatibility, stage an update, or authorize recovery/device writes.
     */
    public static PackageInspection inspectPackage(String displayName, long declaredSize, InputStream input) {
        if (!safePackageName(displayName)) {
            return new PackageInspection(PackageState.REJECTED_NAME, -1L, "");
        }
        if (declaredSize == 0L || declaredSize > MAX_PACKAGE_BYTES) {
            return new PackageInspection(PackageState.REJECTED_SIZE, declaredSize, "");
        }
        if (input == null) {
            return readFailure();
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[64 * 1024];
            byte[] header = new byte[4];
            int headerBytes = 0;
            long total = 0L;
            while (true) {
                if (Thread.currentThread().isInterrupted()) return readFailure();
                int read = input.read(buffer);
                if (read < 0) break;
                if (read == 0) continue;
                if (read > MAX_PACKAGE_BYTES - total) {
                    return new PackageInspection(PackageState.REJECTED_SIZE, total + read, "");
                }
                int copy = Math.min(read, header.length - headerBytes);
                if (copy > 0) {
                    System.arraycopy(buffer, 0, header, headerBytes, copy);
                    headerBytes += copy;
                }
                digest.update(buffer, 0, read);
                total += read;
            }
            if (total == 0L || (declaredSize >= 0L && declaredSize != total)) {
                return new PackageInspection(PackageState.REJECTED_SIZE, total, "");
            }
            if (!looksLikeZipHeader(header, headerBytes)) {
                return new PackageInspection(PackageState.REJECTED_FORMAT, total, "");
            }
            return new PackageInspection(PackageState.REVIEW_READY_UNTRUSTED, total, hex(digest.digest()));
        } catch (Exception ignored) {
            return readFailure();
        }
    }

    public static PackageInspection readFailure() {
        return new PackageInspection(PackageState.READ_FAILED, -1L, "");
    }

    public static boolean safePackageName(String displayName) {
        if (displayName == null || displayName.isEmpty() || displayName.length() > MAX_PACKAGE_NAME_CHARS) return false;
        if (!displayName.equals(displayName.trim()) || displayName.contains("/") || displayName.contains("\\")) return false;
        for (int i = 0; i < displayName.length(); i++) {
            if (Character.isISOControl(displayName.charAt(i))) return false;
        }
        return displayName.toLowerCase(Locale.ROOT).endsWith(".zip") && displayName.length() > 4;
    }

    private static String exactField(String line, String prefix, int maxChars) {
        if (line == null || !line.startsWith(prefix) || line.length() <= prefix.length()) return null;
        String value = line.substring(prefix.length());
        if (value.length() > maxChars || !safeSimpleValue(value, maxChars)) return null;
        return value;
    }

    private static boolean safeSimpleValue(String value, int maxChars) {
        if (value == null || value.isEmpty() || value.length() > maxChars || !value.equals(value.trim())) return false;
        for (int i = 0; i < value.length(); i++) {
            if (Character.isISOControl(value.charAt(i))) return false;
        }
        return value.indexOf('\n') < 0 && value.indexOf('\r') < 0;
    }

    private static boolean isLowerHexSha256(String value) {
        if (value == null || value.length() != 64) return false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) return false;
        }
        return true;
    }

    private static boolean looksLikeZipHeader(byte[] header, int count) {
        return count >= 4
                && (header[0] & 0xff) == 0x50
                && (header[1] & 0xff) == 0x4b
                && (header[2] & 0xff) == 0x03
                && (header[3] & 0xff) == 0x04;
    }

    public static String sha256Hex(byte[] bytes) {
        if (bytes == null) return "";
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return hex(digest.digest(bytes));
        } catch (Exception ignored) {
            return "";
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) builder.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return builder.toString();
    }
}
