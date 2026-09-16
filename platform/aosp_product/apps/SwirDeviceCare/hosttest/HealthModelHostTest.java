package org.swir.phoneos.device_care;

public final class HealthModelHostTest {
    public static void main(String[] args) {
        require(HealthModel.percentUsed(25, 100) == 75);
        require(HealthModel.percentUsed(100, 100) == 0);
        require(HealthModel.percentUsed(-1, 100) == -1);
        require(HealthModel.thermalBand(0) == HealthModel.ThermalBand.NOMINAL);
        require(HealthModel.thermalBand(3) == HealthModel.ThermalBand.WARM);
        require(HealthModel.thermalBand(5) == HealthModel.ThermalBand.HOT);
        require(HealthModel.thermalBand(6) == HealthModel.ThermalBand.CRITICAL);
        require(HealthModel.batteryLevelValid(0));
        require(HealthModel.batteryLevelValid(100));
        require(!HealthModel.batteryLevelValid(101));
    }

    private static void require(boolean value) {
        if (!value) throw new AssertionError("HealthModel contract failed");
    }
}
