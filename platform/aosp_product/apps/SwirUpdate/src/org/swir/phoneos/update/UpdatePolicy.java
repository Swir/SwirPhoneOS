package org.swir.phoneos.update;

import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.Signature;

/** Pure-Java verification and channel policy used by Swir Update. */
public final class UpdatePolicy {
    public enum Channel { STABLE, BETA, DEVELOPER, UNKNOWN }

    private UpdatePolicy() {}

    public static Channel channelForBuild(String type, String tags) {
        String safeType = type == null ? "" : type.trim().toLowerCase();
        String safeTags = tags == null ? "" : tags.trim().toLowerCase();
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

    public static String sha256Hex(byte[] bytes) {
        if (bytes == null) return "";
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] out = digest.digest(bytes);
            StringBuilder builder = new StringBuilder(out.length * 2);
            for (byte value : out) builder.append(String.format("%02x", value & 0xff));
            return builder.toString();
        } catch (Exception ignored) {
            return "";
        }
    }
}
