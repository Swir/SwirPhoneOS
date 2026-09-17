package org.swir.phoneos.camera;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Size;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private TextView report;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.addView(text(R.string.title, 28));
        root.addView(text(R.string.subtitle, 15));
        root.addView(text(R.string.source_stage_notice, 13));
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button refresh = button(R.string.refresh);
        Button photo = button(R.string.photo_handoff);
        Button video = button(R.string.video_handoff);
        actions.addView(refresh, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(photo, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(video, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(actions);
        report = text(R.string.capability_empty, 15);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(report);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        refresh.setOnClickListener(v -> refreshCapabilities());
        photo.setOnClickListener(v -> captureHandoff(MediaStore.ACTION_IMAGE_CAPTURE));
        video.setOnClickListener(v -> captureHandoff(MediaStore.ACTION_VIDEO_CAPTURE));
        refreshCapabilities();
    }

    private TextView text(int id, int sp) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(Color.WHITE);
        view.setPadding(0, 6, 0, 12);
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
        return button;
    }

    private void refreshCapabilities() {
        CameraManager manager = getSystemService(CameraManager.class);
        if (manager == null) {
            report.setText(R.string.capability_empty);
            return;
        }
        try {
            StringBuilder out = new StringBuilder();
            for (String id : manager.getCameraIdList()) {
                CameraCharacteristics info = manager.getCameraCharacteristics(id);
                Integer facing = info.get(CameraCharacteristics.LENS_FACING);
                StreamConfigurationMap map = info.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                Size largest = largestJpeg(map == null ? null : map.getOutputSizes(ImageFormat.JPEG));
                String lens = CameraPolicy.lensLabel(facing == null ? -1 : facing);
                if (largest == null) {
                    out.append(getString(R.string.camera_row, id, lens)).append('\n');
                } else {
                    out.append(getString(R.string.camera_row, id, lens)).append('\n');
                    out.append(getString(R.string.size_row, largest.getWidth(), largest.getHeight(), CameraPolicy.formatMegapixels(largest.getWidth(), largest.getHeight()))).append("\n\n");
                }
            }
            report.setText(out.length() == 0 ? getString(R.string.capability_empty) : out.toString().trim());
        } catch (Exception error) {
            report.setText(R.string.capability_error);
        }
    }

    private static Size largestJpeg(Size[] sizes) {
        if (sizes == null || sizes.length == 0) return null;
        Size best = null;
        long bestArea = -1;
        for (Size size : sizes) {
            if (size == null || !CameraPolicy.validDimensions(size.getWidth(), size.getHeight())) continue;
            long area = (long) size.getWidth() * (long) size.getHeight();
            if (area > bestArea) { bestArea = area; best = size; }
        }
        return best;
    }

    private void captureHandoff(String action) {
        Intent intent = new Intent(action);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.handoff_unavailable, Toast.LENGTH_LONG).show();
    }
}
