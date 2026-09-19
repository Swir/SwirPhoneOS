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

        check(CameraPolicy.normalizeLensFacing(0) == CameraPolicy.LENS_FRONT, "front lens");
        check(CameraPolicy.normalizeLensFacing(1) == CameraPolicy.LENS_BACK, "back lens");
        check(CameraPolicy.normalizeLensFacing(2) == CameraPolicy.LENS_EXTERNAL, "external lens");
        check(CameraPolicy.normalizeLensFacing(99) == CameraPolicy.LENS_UNKNOWN, "unknown lens");
        check(CameraPolicy.normalizeLensFacing(null) == CameraPolicy.LENS_UNKNOWN, "missing lens");
        check(CameraPolicy.nextPreferredLens(CameraPolicy.LENS_BACK) == CameraPolicy.LENS_FRONT, "switch to front");
        check(CameraPolicy.nextPreferredLens(CameraPolicy.LENS_FRONT) == CameraPolicy.LENS_BACK, "switch to back");

        check(CameraPolicy.jpegOrientation(90, 0, false) == 90, "back portrait orientation");
        check(CameraPolicy.jpegOrientation(90, 90, false) == 0, "back landscape orientation");
        check(CameraPolicy.jpegOrientation(270, 90, true) == 0, "front mirrored orientation basis");
        check(CameraPolicy.jpegOrientation(-90, 0, false) == 270, "normalizes negative sensor orientation");
    }
}
