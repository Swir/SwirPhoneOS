package org.swir.phoneos.camera;

public final class CameraPolicyHostTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(CameraPolicy.validDimensions(4000, 3000), "normal dimensions");
        check(!CameraPolicy.validDimensions(0, 3000), "zero width rejected");
        check(!CameraPolicy.validDimensions(50000, 3000), "unbounded width rejected");
        check(Math.abs(CameraPolicy.megapixels(4000, 3000) - 12.0) < 0.001, "megapixels");
        check("12.0".equals(CameraPolicy.formatMegapixels(4000, 3000)), "stable formatting");
        check("FRONT".equals(CameraPolicy.lensLabel(0)), "front lens");
        check("BACK".equals(CameraPolicy.lensLabel(1)), "back lens");
        check("EXTERNAL".equals(CameraPolicy.lensLabel(2)), "external lens");
        check("UNKNOWN".equals(CameraPolicy.lensLabel(99)), "unknown lens");
    }
}
