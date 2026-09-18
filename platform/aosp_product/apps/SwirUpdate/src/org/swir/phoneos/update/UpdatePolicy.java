package org.swir.phoneos.update;

import java.io.InputStream;
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

    /** Hard read ceiling for owner-selected local OTA candidates. */
    public static final long MAX_PACKAGE_BYTES = 16L * 1024L * 1024L * 1024L;
    public static final int MAX_PACKAGE_NAME_CHARS = 180;

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
