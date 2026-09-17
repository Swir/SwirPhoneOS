package org.swir.phoneos.weather;

public final class WeatherPolicyHostTest {
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    public static void main(String[] args) {
        check(WeatherPolicy.validLatitude(62.4722), "latitude");
        check(!WeatherPolicy.validLatitude(91.0), "latitude bound");
        check(WeatherPolicy.validLongitude(6.1495), "longitude");
        check(!WeatherPolicy.validLongitude(-181.0), "longitude bound");
        check(Math.abs(WeatherPolicy.parseCoordinate("62,4722", 0) - 62.4722) < 0.00001, "comma parse");
        check(WeatherPolicy.forecastUrl(62.4722, 6.1495, false).startsWith("https://api.open-meteo.com/"), "https provider");
        check(WeatherPolicy.forecastUrl(200, 0, false).isEmpty(), "invalid coordinate rejected");
        check("fahrenheit".equals(WeatherPolicy.temperatureUnit(true)), "imperial temp");
        check("kmh".equals(WeatherPolicy.windUnit(false)), "metric wind");
        check("https://open-meteo.com/".equals(WeatherPolicy.providerUrl()), "attribution url");
    }
}
