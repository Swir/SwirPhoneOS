package org.swir.phoneos.camera;

import android.Manifest;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.HandlerThread;
import android.provider.MediaStore;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION_REQUEST = 4101;

    private TextureView preview;
    private TextView status;
    private TextView report;
    private Button capture;
    private Button switchLens;
    private CameraDevice cameraDevice;
    private CameraCaptureSession captureSession;
    private CaptureRequest.Builder previewRequest;
    private ImageReader imageReader;
    private HandlerThread backgroundThread;
    private Handler backgroundHandler;
    private Surface previewSurface;
    private Uri pendingPhotoUri;
    private int preferredLens = CameraPolicy.LENS_BACK;
    private String activeCameraId;
    private boolean activeFrontFacing;
    private int activeSensorOrientation;
    private boolean opening;

    private final TextureView.SurfaceTextureListener textureListener = new TextureView.SurfaceTextureListener() {
        @Override public void onSurfaceTextureAvailable(SurfaceTexture surface, int width, int height) { openCameraIfReady(); }
        @Override public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int width, int height) { }
        @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) { return true; }
        @Override public void onSurfaceTextureUpdated(SurfaceTexture surface) { }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pagePadding = dim(R.dimen.swir_space_lg);
        root.setPadding(pagePadding, pagePadding, pagePadding, pagePadding);
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.addView(text(R.string.title, 28, R.color.swir_text_primary));
        root.addView(text(R.string.subtitle, 15, R.color.swir_text_secondary));
        root.addView(text(R.string.source_stage_notice, 13, R.color.swir_accent_cyan));

        preview = new TextureView(this);
        preview.setSurfaceTextureListener(textureListener);
        preview.setContentDescription(getString(R.string.preview_content_description));
        root.addView(preview, new LinearLayout.LayoutParams(-1, 0, 3));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        capture = button(R.string.capture_photo);
        switchLens = button(R.string.switch_camera);
        Button video = button(R.string.video_handoff);
        Button refresh = button(R.string.refresh);
        actions.addView(capture, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(switchLens, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(video, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(refresh, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(actions);

        status = text(R.string.camera_starting, 14, R.color.swir_accent_cyan);
        root.addView(status);
        report = text(R.string.capability_empty, 14, R.color.swir_text_primary);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(report);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);

        capture.setEnabled(false);
        capture.setOnClickListener(v -> captureStill());
        switchLens.setOnClickListener(v -> switchCamera());
        video.setOnClickListener(v -> captureHandoff(MediaStore.ACTION_VIDEO_CAPTURE));
        refresh.setOnClickListener(v -> refreshCapabilities());
        refreshCapabilities();
    }

    @Override protected void onResume() {
        super.onResume();
        startBackgroundThread();
        if (preview.isAvailable()) openCameraIfReady();
    }

    @Override protected void onPause() {
        closeCamera();
        stopBackgroundThread();
        super.onPause();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            openCameraIfReady();
        } else {
            status.setText(R.string.permission_required);
            capture.setEnabled(false);
        }
    }

    private TextView text(int id, int sp, int colorRes) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(getColor(colorRes));
        view.setPadding(0, dim(R.dimen.swir_space_xs), 0, dim(R.dimen.swir_space_sm));
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
        button.setMinHeight(dim(R.dimen.swir_touch_min));
        return button;
    }

    private void startBackgroundThread() {
        if (backgroundThread != null) return;
        backgroundThread = new HandlerThread("SwirCamera");
        backgroundThread.start();
        backgroundHandler = new Handler(backgroundThread.getLooper());
    }

    private void stopBackgroundThread() {
        HandlerThread thread = backgroundThread;
        backgroundThread = null;
        backgroundHandler = null;
        if (thread == null) return;
        thread.quitSafely();
        try { thread.join(1500); } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
    }

    private void openCameraIfReady() {
        if (!preview.isAvailable() || backgroundHandler == null || opening || cameraDevice != null) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] { Manifest.permission.CAMERA }, CAMERA_PERMISSION_REQUEST);
            return;
        }

        CameraManager manager = getSystemService(CameraManager.class);
        if (manager == null) {
            status.setText(R.string.capability_empty);
            return;
        }
        try {
            String selected = selectCameraId(manager, preferredLens);
            if (selected == null) {
                status.setText(R.string.capability_empty);
                return;
            }
            CameraCharacteristics info = manager.getCameraCharacteristics(selected);
            StreamConfigurationMap map = info.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
            Size jpeg = largestJpeg(map == null ? null : map.getOutputSizes(ImageFormat.JPEG));
            Size previewSize = choosePreviewSize(map == null ? null : map.getOutputSizes(SurfaceTexture.class));
            if (jpeg == null || previewSize == null) {
                status.setText(R.string.capture_configuration_unavailable);
                return;
            }

            closeImageReader();
            imageReader = ImageReader.newInstance(jpeg.getWidth(), jpeg.getHeight(), ImageFormat.JPEG, 2);
            imageReader.setOnImageAvailableListener(this::onImageAvailable, backgroundHandler);
            SurfaceTexture texture = preview.getSurfaceTexture();
            if (texture == null) {
                status.setText(R.string.capture_configuration_unavailable);
                closeImageReader();
                return;
            }
            texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
            previewSurface = new Surface(texture);

            Integer facing = info.get(CameraCharacteristics.LENS_FACING);
            Integer orientation = info.get(CameraCharacteristics.SENSOR_ORIENTATION);
            activeFrontFacing = CameraPolicy.normalizeLensFacing(facing) == CameraPolicy.LENS_FRONT;
            activeSensorOrientation = orientation == null ? 0 : orientation.intValue();
            activeCameraId = selected;
            opening = true;
            status.setText(R.string.camera_starting);
            manager.openCamera(selected, cameraStateCallback, backgroundHandler);
        } catch (SecurityException denied) {
            status.setText(R.string.permission_required);
        } catch (CameraAccessException | IllegalArgumentException error) {
            status.setText(R.string.camera_open_failed);
            opening = false;
        }
    }

    private final CameraDevice.StateCallback cameraStateCallback = new CameraDevice.StateCallback() {
        @Override public void onOpened(CameraDevice camera) {
            opening = false;
            cameraDevice = camera;
            createPreviewSession();
        }

        @Override public void onDisconnected(CameraDevice camera) {
            opening = false;
            camera.close();
            if (cameraDevice == camera) cameraDevice = null;
            runOnUiThread(() -> {
                capture.setEnabled(false);
                status.setText(R.string.camera_disconnected);
            });
        }

        @Override public void onError(CameraDevice camera, int error) {
            opening = false;
            camera.close();
            if (cameraDevice == camera) cameraDevice = null;
            runOnUiThread(() -> {
                capture.setEnabled(false);
                status.setText(R.string.camera_open_failed);
            });
        }
    };

    private void createPreviewSession() {
        CameraDevice camera = cameraDevice;
        ImageReader reader = imageReader;
        Surface surface = previewSurface;
        if (camera == null || reader == null || surface == null) return;
        try {
            previewRequest = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            previewRequest.addTarget(surface);
            previewRequest.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            List<Surface> outputs = new ArrayList<>();
            outputs.add(surface);
            outputs.add(reader.getSurface());
            camera.createCaptureSession(outputs, new CameraCaptureSession.StateCallback() {
                @Override public void onConfigured(CameraCaptureSession session) {
                    if (cameraDevice == null) {
                        session.close();
                        return;
                    }
                    captureSession = session;
                    try {
                        session.setRepeatingRequest(previewRequest.build(), null, backgroundHandler);
                        runOnUiThread(() -> {
                            capture.setEnabled(true);
                            status.setText(R.string.camera_ready);
                        });
                    } catch (CameraAccessException error) {
                        runOnUiThread(() -> status.setText(R.string.camera_open_failed));
                    }
                }

                @Override public void onConfigureFailed(CameraCaptureSession session) {
                    runOnUiThread(() -> {
                        capture.setEnabled(false);
                        status.setText(R.string.capture_configuration_unavailable);
                    });
                }
            }, backgroundHandler);
        } catch (CameraAccessException error) {
            status.setText(R.string.camera_open_failed);
        }
    }

    private void captureStill() {
        CameraDevice camera = cameraDevice;
        CameraCaptureSession session = captureSession;
        ImageReader reader = imageReader;
        if (camera == null || session == null || reader == null || pendingPhotoUri != null) return;
        Uri uri = createPendingPhoto();
        if (uri == null) {
            status.setText(R.string.save_failed);
            return;
        }
        pendingPhotoUri = uri;
        capture.setEnabled(false);
        status.setText(R.string.capturing_photo);
        try {
            CaptureRequest.Builder request = camera.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
            request.addTarget(reader.getSurface());
            request.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            request.set(CaptureRequest.JPEG_ORIENTATION,
                    CameraPolicy.jpegOrientation(activeSensorOrientation, displayRotationDegrees(), activeFrontFacing));
            session.capture(request.build(), new CameraCaptureSession.CaptureCallback() {
                @Override public void onCaptureFailed(CameraCaptureSession session, CaptureRequest request,
                        android.hardware.camera2.CaptureFailure failure) {
                    failPendingPhoto();
                }

                @Override public void onCaptureCompleted(CameraCaptureSession session, CaptureRequest request,
                        TotalCaptureResult result) {
                    // ImageReader owns byte delivery. Success is reported only after bytes are committed.
                }
            }, backgroundHandler);
        } catch (CameraAccessException error) {
            failPendingPhoto();
        }
    }

    private void onImageAvailable(ImageReader reader) {
        try (Image image = reader.acquireNextImage()) {
            if (image == null) return;
            Uri uri = pendingPhotoUri;
            if (uri == null) return;
            ByteBuffer buffer = image.getPlanes()[0].getBuffer();
            byte[] bytes = new byte[buffer.remaining()];
            buffer.get(bytes);
            try (OutputStream out = getContentResolver().openOutputStream(uri, "w")) {
                if (out == null) throw new IllegalStateException("MediaStore output unavailable");
                out.write(bytes);
                out.flush();
            }
            ContentValues done = new ContentValues();
            done.put(MediaStore.Images.Media.IS_PENDING, 0);
            getContentResolver().update(uri, done, null, null);
            pendingPhotoUri = null;
            runOnUiThread(() -> {
                capture.setEnabled(captureSession != null);
                status.setText(R.string.photo_saved);
                Toast.makeText(this, R.string.photo_saved, Toast.LENGTH_SHORT).show();
            });
        } catch (Exception error) {
            failPendingPhoto();
        }
    }

    private Uri createPendingPhoto() {
        ContentValues values = new ContentValues();
        String stamp = new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.ROOT).format(new Date());
        values.put(MediaStore.Images.Media.DISPLAY_NAME, "SWIR_" + stamp + ".jpg");
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
        values.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/SwirPhoneOS");
        values.put(MediaStore.Images.Media.IS_PENDING, 1);
        try {
            return getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
        } catch (RuntimeException error) {
            return null;
        }
    }

    private void failPendingPhoto() {
        Uri uri = pendingPhotoUri;
        pendingPhotoUri = null;
        if (uri != null) {
            try { getContentResolver().delete(uri, null, null); } catch (RuntimeException ignored) { }
        }
        runOnUiThread(() -> {
            capture.setEnabled(captureSession != null);
            status.setText(R.string.save_failed);
        });
    }

    private void switchCamera() {
        preferredLens = CameraPolicy.nextPreferredLens(preferredLens);
        closeCamera();
        status.setText(R.string.camera_starting);
        openCameraIfReady();
    }

    private String selectCameraId(CameraManager manager, int preferred) throws CameraAccessException {
        String fallback = null;
        for (String id : manager.getCameraIdList()) {
            if (fallback == null) fallback = id;
            CameraCharacteristics info = manager.getCameraCharacteristics(id);
            if (CameraPolicy.normalizeLensFacing(info.get(CameraCharacteristics.LENS_FACING)) == preferred) return id;
        }
        return fallback;
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
                int facing = CameraPolicy.normalizeLensFacing(info.get(CameraCharacteristics.LENS_FACING));
                StreamConfigurationMap map = info.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                Size largest = largestJpeg(map == null ? null : map.getOutputSizes(ImageFormat.JPEG));
                out.append(getString(R.string.camera_row, id, getString(lensString(facing)))).append('\n');
                if (largest != null) {
                    out.append(getString(R.string.size_row, largest.getWidth(), largest.getHeight(),
                            CameraPolicy.formatMegapixels(largest.getWidth(), largest.getHeight()))).append("\n\n");
                }
            }
            report.setText(out.length() == 0 ? getString(R.string.capability_empty) : out.toString().trim());
        } catch (Exception error) {
            report.setText(R.string.capability_error);
        }
    }

    private int lensString(int facing) {
        if (facing == CameraPolicy.LENS_FRONT) return R.string.lens_front;
        if (facing == CameraPolicy.LENS_BACK) return R.string.lens_back;
        if (facing == CameraPolicy.LENS_EXTERNAL) return R.string.lens_external;
        return R.string.lens_unknown;
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

    private static Size choosePreviewSize(Size[] sizes) {
        if (sizes == null || sizes.length == 0) return null;
        Size best = null;
        long target = 1920L * 1080L;
        long bestDistance = Long.MAX_VALUE;
        for (Size size : sizes) {
            if (size == null || !CameraPolicy.validDimensions(size.getWidth(), size.getHeight())) continue;
            long area = (long) size.getWidth() * (long) size.getHeight();
            long distance = Math.abs(area - target);
            if (distance < bestDistance) { bestDistance = distance; best = size; }
        }
        return best;
    }

    private int displayRotationDegrees() {
        if (getDisplay() == null) return 0;
        int rotation = getDisplay().getRotation();
        if (rotation == Surface.ROTATION_90) return 90;
        if (rotation == Surface.ROTATION_180) return 180;
        if (rotation == Surface.ROTATION_270) return 270;
        return 0;
    }

    private void captureHandoff(String action) {
        Intent intent = new Intent(action);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.handoff_unavailable, Toast.LENGTH_LONG).show();
    }

    private void closeCamera() {
        opening = false;
        CameraCaptureSession session = captureSession;
        captureSession = null;
        if (session != null) session.close();
        CameraDevice camera = cameraDevice;
        cameraDevice = null;
        if (camera != null) camera.close();
        closeImageReader();
        Surface surface = previewSurface;
        previewSurface = null;
        if (surface != null) surface.release();
        activeCameraId = null;
        capture.setEnabled(false);
    }

    private void closeImageReader() {
        ImageReader reader = imageReader;
        imageReader = null;
        if (reader != null) reader.close();
    }

    private int dim(int id) { return getResources().getDimensionPixelSize(id); }
}
