package org.swir.phoneos.device_care;

/** Pure-Java calculations used by Swir Device Care and verified by host CI. */
public final class HealthModel {
    public enum ThermalBand { NOMINAL, WARM, HOT, CRITICAL, UNKNOWN }

    private HealthModel() {}

    public static int percentUsed(long availableBytes, long totalBytes) {
        if (availableBytes < 0 || totalBytes <= 0 || availableBytes > totalBytes) return -1;
        long used = totalBytes - availableBytes;
        return (int) Math.min(100L, Math.max(0L, Math.round((used * 100.0d) / totalBytes)));
    }

    public static ThermalBand thermalBand(int androidThermalStatus) {
        if (androidThermalStatus < 0) return ThermalBand.UNKNOWN;
        if (androidThermalStatus <= 1) return ThermalBand.NOMINAL;
        if (androidThermalStatus <= 3) return ThermalBand.WARM;
        if (androidThermalStatus <= 5) return ThermalBand.HOT;
        return ThermalBand.CRITICAL;
    }

    public static boolean batteryLevelValid(int level) {
        return level >= 0 && level <= 100;
    }
}
