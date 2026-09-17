package org.swir.phoneos.weather;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.net.ssl.HttpsURLConnection;

public final class MainActivity extends Activity {
    private static final int MAX_RESPONSE_CHARS = 262144;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText latitude;
    private EditText longitude;
    private CheckBox imperial;
    private TextView result;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.addView(text(R.string.title, 28));
        root.addView(text(R.string.subtitle, 14));
        latitude = field(R.string.latitude_hint);
        longitude = field(R.string.longitude_hint);
        root.addView(latitude);
        root.addView(longitude);
        imperial = new CheckBox(this);
        imperial.setText(R.string.imperial);
        imperial.setTextColor(Color.WHITE);
        root.addView(imperial);
        Button refresh = button(R.string.refresh);
        Button provider = button(R.string.provider);
        root.addView(refresh);
        root.addView(provider);
        result = text(R.string.loading, 16);
        root.addView(result);
        setContentView(root);
        android.content.SharedPreferences prefs = getSharedPreferences("weather", MODE_PRIVATE);
        latitude.setText(prefs.getString("latitude", "62.4722"));
        longitude.setText(prefs.getString("longitude", "6.1495"));
        imperial.setChecked(prefs.getBoolean("imperial", false));
        refresh.setOnClickListener(v -> refreshForecast());
        provider.setOnClickListener(v -> openProvider());
        refreshForecast();
    }

    private TextView text(int id, int sp) {
        TextView view = new TextView(this); view.setText(id); view.setTextSize(sp); view.setTextColor(Color.WHITE); view.setPadding(0, 6, 0, 10); return view;
    }
    private EditText field(int hint) {
        EditText view = new EditText(this); view.setHint(hint); view.setSingleLine(true); view.setTextColor(Color.WHITE); view.setHintTextColor(Color.rgb(130, 170, 190)); return view;
    }
    private Button button(int id) { Button button = new Button(this); button.setText(id); return button; }

    private void refreshForecast() {
        double lat = WeatherPolicy.parseCoordinate(latitude.getText().toString(), Double.NaN);
        double lon = WeatherPolicy.parseCoordinate(longitude.getText().toString(), Double.NaN);
        boolean useImperial = imperial.isChecked();
        String endpoint = WeatherPolicy.forecastUrl(lat, lon, useImperial);
        if (endpoint.isEmpty()) { result.setText(R.string.invalid_coordinates); return; }
        getSharedPreferences("weather", MODE_PRIVATE).edit().putString("latitude", latitude.getText().toString()).putString("longitude", longitude.getText().toString()).putBoolean("imperial", useImperial).apply();
        result.setText(R.string.loading);
        executor.execute(() -> fetch(endpoint, useImperial));
    }

    private void fetch(String endpoint, boolean useImperial) {
        HttpsURLConnection connection = null;
        try {
            connection = (HttpsURLConnection) new URL(endpoint).openConnection();
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(8000);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("User-Agent", "SwirPhoneOS-Weather/1");
            if (connection.getResponseCode() != 200) throw new IllegalStateException();
            StringBuilder body = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                char[] buffer = new char[4096]; int read;
                while ((read = reader.read(buffer)) != -1) { body.append(buffer, 0, read); if (body.length() > MAX_RESPONSE_CHARS) throw new IllegalStateException(); }
            }
            JSONObject current = new JSONObject(body.toString()).getJSONObject("current");
            double temperature = current.getDouble("temperature_2m");
            double wind = current.getDouble("wind_speed_10m");
            int code = current.getInt("weather_code");
            runOnUiThread(() -> result.setText(getString(R.string.weather_result, temperature, getString(useImperial ? R.string.unit_imperial : R.string.unit_metric), wind, code)));
        } catch (Exception error) {
            runOnUiThread(() -> result.setText(R.string.network_error));
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void openProvider() {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(WeatherPolicy.providerUrl()));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.provider_unavailable, Toast.LENGTH_LONG).show();
    }

    @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }
}
