package org.swir.phoneos.privacy;

import java.util.List;

public final class PermissionReviewPolicyHostTest {
    public static void main(String[] args) {
        List<String> packages = PermissionReviewPolicy.betaSurfacePackages();
        check(packages.size() == PermissionReviewPolicy.MAX_PACKAGES, "beta package count");
        check(packages.contains("org.swir.phoneos.launcher"), "launcher included");
        check(packages.contains("org.swir.phoneos.swirroot"), "swirroot included");
        check(packages.contains("org.swir.phoneos.privacy"), "privacy included");

        check("Swir Privacy".equals(
                PermissionReviewPolicy.normalizeLabel("  Swir\n\t Privacy\u0000  ")),
                "label sanitization");
        String emoji = "🔒".repeat(100);
        check(PermissionReviewPolicy.normalizeLabel(emoji).codePointCount(
                0, PermissionReviewPolicy.normalizeLabel(emoji).length()) == 72,
                "unicode label bound");

        check("CAMERA".equals(
                PermissionReviewPolicy.shortPermissionName("android.permission.CAMERA")),
                "permission short name");
        check(PermissionReviewPolicy.shortPermissionName("android.permission.CAM ERA").isEmpty(),
                "malformed permission rejected");

        String[] many = new String[40];
        for (int i = 0; i < many.length; i++) many[i] = "org.test.permission.P" + i;
        check(PermissionReviewPolicy.boundedPermissions(many).size()
                == PermissionReviewPolicy.MAX_PERMISSIONS_PER_PACKAGE,
                "permission bound");
        check(PermissionReviewPolicy.boundedPermissions(new String[]{
                "android.permission.CAMERA",
                "android.permission.CAMERA",
                "android.permission.RECORD_AUDIO"
        }).size() == 2, "dedupe");

        List<String> permissions = PermissionReviewPolicy.boundedPermissions(new String[]{
                "android.permission.CAMERA"
        });
        check(PermissionReviewPolicy.matches("camera", "Swir Camera", permissions), "permission search");
        check(PermissionReviewPolicy.matches("swir", "Swir Privacy", permissions), "label search");
        check(!PermissionReviewPolicy.matches("missing", "Swir Privacy", permissions), "missing search");
    }

    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }
}
