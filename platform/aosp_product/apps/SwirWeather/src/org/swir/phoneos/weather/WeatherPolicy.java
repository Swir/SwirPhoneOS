package org.swir.phoneos.weather;

import java.util.Locale;

public final class WeatherPolicy {
    private WeatherPolicy() {}

    public static boolean validLatitude(double value) { return !Double.isNaN(value) && !Double.isInfinite(value) && value >= -90.0 && value <= 90.0; }
    public static boolean validLongitude(double value) { return !Double.isNaN(value) && !Double.isInfinite(value) && value >= -180.0 && value <= 180.0; }

    public static double parseCoordinate(String raw, double fallback) {
        if (raw == null) return fallback;
        try { return Double.parseDouble(raw.trim().replace(',', '.')); }
        catch (RuntimeException error) { return fallback; }
    }

    public static String temperatureUnit(boolean imperial) { return imperial ? "fahrenheit" : "celsius"; }
    public static String windUnit(boolean imperial) { return imperial ? "mph" : "kmh"; }

    public static String forecastUrl(double latitude, double longitude, boolean imperial) {
        if (!validLatitude(latitude) || !validLongitude(longitude)) return "";
        return String.format(Locale.ROOT,
                "https://api.open-meteo.com/v1/forecast?latitude=%.5f&longitude=%.5f&current=temperature_2m,wind_speed_10m,weather_code&temperature_unit=%s&wind_speed_unit=%s&timezone=auto",
                latitude, longitude, temperatureUnit(imperial), windUnit(imperial));
    }

    public static String providerUrl() { return "https://open-meteo.com/"; }
}
