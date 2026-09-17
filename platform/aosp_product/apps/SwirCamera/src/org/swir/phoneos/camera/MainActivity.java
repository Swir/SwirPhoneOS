package org.swir.phoneos.camera;

import android.Manifest;
import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.provider.MediaStore;
import android.util.Size;
import android.view.Gravity;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.IOException;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.Comparator;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION_REQUEST = 2401;

    private TextureView preview;
    private TextView status;
    private TextView capability;
    private Button photoButton;
    private Button videoButton;
    private Button switchButton;

    private CameraManager cameraManager;
    private CameraDevice cameraDevice;
    private CameraCaptureSession captureSession;
    private ImageReader imageReader;
    private MediaRecorder mediaRecorder;
    private ParcelFileDescriptor videoDescriptor;
    private Uri pendingVideoUri;

    private Size previewSize;
    private Size photoSize;
    private Size videoSize;
    private String cameraId;
    private int cameraCount;
    private int sensorOrientation;
    private boolean preferFront;
    private boolean videoStarting;
    private boolean recording;
    private long recordingStartedAt;

    private final TextureView.SurfaceTextureListener surfaceListener = new TextureView.SurfaceTextureListener() {
        @Override
        public void onSurfaceTextureAvailable(SurfaceTexture surface, int width, int height) {
            openCamera();
        }

        @Override
        public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int width, int height) { }

        @Override
        public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) {
            return true;
        }

        @Override
        public void onSurfaceTextureUpdated(SurfaceTexture surface) { }
    };

    private final CameraDevice.StateCallback cameraStateCallback = new CameraDevice.StateCallback() {
        @Override
        public void onOpened(CameraDevice camera) {
            cameraDevice = camera;
            status.setText(R.string.status_ready);
            startPreview();
            refreshControls();
        }

        @Override
        public void onDisconnected(CameraDevice camera) {
            camera.close();
            cameraDevice = null;
            status.setText(R.string.status_disconnected);
            refreshControls();
        }

        @Override
        public void onError(CameraDevice camera, int error) {
            camera.close();
            cameraDevice = null;
            status.setText(getString(R.string.status_camera_error, error));
            refreshControls();
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        cameraManager = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
        setContentView(buildContent());
        preview.setSurfaceTextureListener(surfaceListener);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (preview.isAvailable()) {
            openCamera();
        }
    }

    @Override
    protected void onPause() {
        if (recording) {
            stopVideo(false);
        } else if (videoStarting || pendingVideoUri != null || mediaRecorder != null) {
            abortPendingVideo();
        }
        closeCamera();
        super.onPause();
    }

    private View buildContent() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 24, 24, 24);
        root.setBackgroundColor(Color.rgb(5, 14, 22));

        TextView title = new TextView(this);
        title.setText(R.string.app_name);
        title.setTextColor(Color.WHITE);
        title.setTextSize(24f);
        title.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        status = new TextView(this);
        status.setText(R.string.status_waiting);
        status.setTextColor(Color.rgb(79, 223, 255));
        status.setPadding(0, 10, 0, 10);
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));

        preview = new TextureView(this);
        root.addView(preview, new LinearLayout.LayoutParams(-1, 0, 1f));

        capability = new TextView(this);
        capability.setText(R.string.capability_waiting);
        capability.setTextColor(Color.rgb(190, 211, 221));
        capability.setPadding(0, 12, 0, 12);
        root.addView(capability, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setGravity(Gravity.CENTER);

        switchButton = new Button(this);
        switchButton.setText(R.string.switch_camera);
        switchButton.setOnClickListener(v -> switchCamera());
        controls.addView(switchButton, new LinearLayout.LayoutParams(0, -2, 1f));

        photoButton = new Button(this);
        photoButton.setText(R.string.take_photo);
        photoButton.setOnClickListener(v -> capturePhoto());
        controls.addView(photoButton, new LinearLayout.LayoutParams(0, -2, 1f));

        videoButton = new Button(this);
        videoButton.setText(R.string.start_video);
        videoButton.setOnClickListener(v -> {
            if (recording) {
                stopVideo(true);
            } else {
                startVideo();
            }
        });
        controls.addView(videoButton, new LinearLayout.LayoutParams(0, -2, 1f));

        root.addView(controls, new LinearLayout.LayoutParams(-1, -2));
        refreshControls();
        return root;
    }

    private boolean cameraPermissionGranted() {
        return checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    private void openCamera() {
        if (cameraDevice != null || cameraManager == null || !preview.isAvailable()) {
            return;
        }
        if (!cameraPermissionGranted()) {
            status.setText(R.string.status_permission_required);
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
            return;
        }
        try {
            configureCamera();
            cameraManager.openCamera(cameraId, cameraStateCallback, null);
            status.setText(R.string.status_opening);
        } catch (CameraAccessException | SecurityException exc) {
            status.setText(R.string.status_open_failed);
        }
    }

    private void configureCamera() throws CameraAccessException {
        String[] ids = cameraManager.getCameraIdList();
        cameraCount = ids.length;
        if (cameraCount == 0) {
            throw new CameraAccessException(CameraAccessException.CAMERA_ERROR);
        }

        String selected = null;
        int desiredFacing = preferFront
                ? CameraCharacteristics.LENS_FACING_FRONT
                : CameraCharacteristics.LENS_FACING_BACK;
        for (String id : ids) {
            CameraCharacteristics chars = cameraManager.getCameraCharacteristics(id);
            Integer facing = chars.get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == desiredFacing) {
                selected = id;
                break;
            }
        }
        if (selected == null) {
            selected = ids[0];
        }
        cameraId = selected;

        CameraCharacteristics chars = cameraManager.getCameraCharacteristics(cameraId);
        Integer orientation = chars.get(CameraCharacteristics.SENSOR_ORIENTATION);
        sensorOrientation = orientation == null ? 0 : orientation;
        StreamConfigurationMap map = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
        if (map == null) {
            throw new CameraAccessException(CameraAccessException.CAMERA_ERROR);
        }

        previewSize = chooseSize(
                map.getOutputSizes(SurfaceTexture.class),
                Math.max(1, preview.getWidth()),
                Math.max(1, preview.getHeight()));
        photoSize = largest(map.getOutputSizes(ImageFormat.JPEG));
        videoSize = chooseSize(map.getOutputSizes(MediaRecorder.class), 1920, 1080);
        if (previewSize == null || photoSize == null || videoSize == null) {
            throw new CameraAccessException(CameraAccessException.CAMERA_ERROR);
        }

        if (imageReader != null) {
            imageReader.close();
        }
        imageReader = ImageReader.newInstance(
                photoSize.getWidth(),
                photoSize.getHeight(),
                ImageFormat.JPEG,
                2);
        imageReader.setOnImageAvailableListener(this::savePhoto, null);

        Integer facing = chars.get(CameraCharacteristics.LENS_FACING);
        Integer level = chars.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL);
        capability.setText(getString(
                R.string.capability_report,
                cameraCount,
                lensName(facing),
                level == null ? -1 : level,
                photoSize.getWidth(),
                photoSize.getHeight(),
                videoSize.getWidth(),
                videoSize.getHeight()));
    }

    private Size chooseSize(Size[] sizes, int targetWidth, int targetHeight) {
        if (sizes == null || sizes.length == 0) {
            return null;
        }
        int[][] raw = new int[sizes.length][2];
        for (int i = 0; i < sizes.length; i++) {
            raw[i][0] = sizes[i].getWidth();
            raw[i][1] = sizes[i].getHeight();
        }
        int index = CameraPolicy.pickBestSizeIndex(raw, targetWidth, targetHeight);
        return index < 0 ? sizes[0] : sizes[index];
    }

    private Size largest(Size[] sizes) {
        if (sizes == null || sizes.length == 0) {
            return null;
        }
        return Arrays.stream(sizes)
                .max(Comparator.comparingLong(size -> (long) size.getWidth() * size.getHeight()))
                .orElse(sizes[0]);
    }

    private String lensName(Integer facing) {
        if (facing == null) {
            return getString(R.string.lens_unknown);
        }
        if (facing == CameraCharacteristics.LENS_FACING_BACK) {
            return getString(R.string.lens_back);
        }
        if (facing == CameraCharacteristics.LENS_FACING_FRONT) {
            return getString(R.string.lens_front);
        }
        if (facing == CameraCharacteristics.LENS_FACING_EXTERNAL) {
            return getString(R.string.lens_external);
        }
        return getString(R.string.lens_unknown);
    }

    private void startPreview() {
        if (cameraDevice == null || imageReader == null || previewSize == null || videoStarting || recording) {
            return;
        }
        SurfaceTexture texture = preview.getSurfaceTexture();
        if (texture == null) {
            return;
        }
        texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
        Surface surface = new Surface(texture);
        try {
            CaptureRequest.Builder builder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            builder.addTarget(surface);
            builder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            cameraDevice.createCaptureSession(
                    Arrays.asList(surface, imageReader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            if (cameraDevice == null || videoStarting || recording) {
                                session.close();
                                return;
                            }
                            captureSession = session;
                            try {
                                session.setRepeatingRequest(builder.build(), null, null);
                                status.setText(R.string.status_ready);
                            } catch (CameraAccessException | IllegalStateException exc) {
                                status.setText(R.string.status_preview_failed);
                            }
                            refreshControls();
                        }

                        @Override
                        public void onConfigureFailed(CameraCaptureSession session) {
                            session.close();
                            status.setText(R.string.status_preview_failed);
                            refreshControls();
                        }
                    },
                    null);
        } catch (CameraAccessException | IllegalStateException exc) {
            status.setText(R.string.status_preview_failed);
        }
    }

    private void capturePhoto() {
        boolean ready = CameraPolicy.canCapture(
                cameraPermissionGranted(),
                cameraDevice != null,
                captureSession != null && !videoStarting && !recording,
                imageReader != null);
        if (!ready) {
            status.setText(R.string.status_not_ready);
            return;
        }
        try {
            CaptureRequest.Builder still = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
            still.addTarget(imageReader.getSurface());
            still.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            still.set(CaptureRequest.JPEG_ORIENTATION, CameraPolicy.normalizeRotation(sensorOrientation));
            captureSession.capture(still.build(), null, null);
            status.setText(R.string.status_capturing_photo);
        } catch (CameraAccessException | IllegalStateException exc) {
            status.setText(R.string.status_photo_failed);
        }
    }

    private void savePhoto(ImageReader reader) {
        Image image = reader.acquireLatestImage();
        if (image == null) {
            return;
        }
        Uri uri = null;
        try {
            byte[] data = new byte[image.getPlanes()[0].getBuffer().remaining()];
            image.getPlanes()[0].getBuffer().get(data);
            ContentResolver resolver = getContentResolver();
            ContentValues values = new ContentValues();
            values.put(MediaStore.Images.Media.DISPLAY_NAME,
                    CameraPolicy.safeMediaName("SwirPhoto", System.currentTimeMillis(), "jpg"));
            values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            values.put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/SwirPhoneOS");
            values.put(MediaStore.Images.Media.IS_PENDING, 1);
            uri = resolver.insert(
                    MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    values);
            if (uri == null) {
                throw new IOException();
            }
            try (OutputStream out = resolver.openOutputStream(uri, "w")) {
                if (out == null) {
                    throw new IOException();
                }
                out.write(data);
            }
            values.clear();
            values.put(MediaStore.Images.Media.IS_PENDING, 0);
            if (resolver.update(uri, values, null, null) != 1) {
                throw new IOException();
            }
            status.setText(R.string.status_photo_saved);
        } catch (IOException | RuntimeException exc) {
            if (uri != null) {
                getContentResolver().delete(uri, null, null);
            }
            status.setText(R.string.status_photo_failed);
        } finally {
            image.close();
        }
    }

    private void startVideo() {
        boolean ready = CameraPolicy.canCapture(
                cameraPermissionGranted(),
                cameraDevice != null,
                captureSession != null,
                videoSize != null);
        if (!ready || recording || videoStarting || pendingVideoUri != null) {
            status.setText(R.string.status_not_ready);
            return;
        }
        SurfaceTexture texture = preview.getSurfaceTexture();
        if (texture == null) {
            status.setText(R.string.status_not_ready);
            return;
        }

        videoStarting = true;
        refreshControls();
        try {
            prepareVideoRecorder();
            texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
            Surface previewSurface = new Surface(texture);
            Surface recordSurface = mediaRecorder.getSurface();
            CaptureRequest.Builder record = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_RECORD);
            record.addTarget(previewSurface);
            record.addTarget(recordSurface);
            record.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_VIDEO);

            if (captureSession != null) {
                captureSession.close();
                captureSession = null;
            }
            cameraDevice.createCaptureSession(
                    Arrays.asList(previewSurface, recordSurface),
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            if (cameraDevice == null || !videoStarting) {
                                session.close();
                                abortPendingVideo();
                                return;
                            }
                            captureSession = session;
                            try {
                                session.setRepeatingRequest(record.build(), null, null);
                                mediaRecorder.start();
                                videoStarting = false;
                                recording = true;
                                recordingStartedAt = System.currentTimeMillis();
                                status.setText(R.string.status_recording);
                                refreshControls();
                            } catch (CameraAccessException | IllegalStateException | RuntimeException exc) {
                                abortPendingVideo();
                                status.setText(R.string.status_video_failed);
                                startPreview();
                            }
                        }

                        @Override
                        public void onConfigureFailed(CameraCaptureSession session) {
                            session.close();
                            abortPendingVideo();
                            status.setText(R.string.status_video_failed);
                            startPreview();
                        }
                    },
                    null);
        } catch (CameraAccessException | IOException | IllegalStateException | RuntimeException exc) {
            abortPendingVideo();
            status.setText(R.string.status_video_failed);
            startPreview();
        }
    }

    private void prepareVideoRecorder() throws IOException {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.DISPLAY_NAME,
                CameraPolicy.safeMediaName("SwirVideo", System.currentTimeMillis(), "mp4"));
        values.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        values.put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/SwirPhoneOS");
        values.put(MediaStore.Video.Media.IS_PENDING, 1);
        pendingVideoUri = getContentResolver().insert(
                MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                values);
        if (pendingVideoUri == null) {
            throw new IOException();
        }
        videoDescriptor = getContentResolver().openFileDescriptor(pendingVideoUri, "w");
        if (videoDescriptor == null) {
            throw new IOException();
        }

        mediaRecorder = new MediaRecorder(this);
        mediaRecorder.setVideoSource(MediaRecorder.VideoSource.SURFACE);
        mediaRecorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
        mediaRecorder.setVideoEncoder(MediaRecorder.VideoEncoder.H264);
        mediaRecorder.setVideoEncodingBitRate(10_000_000);
        mediaRecorder.setVideoFrameRate(30);
        mediaRecorder.setVideoSize(videoSize.getWidth(), videoSize.getHeight());
        mediaRecorder.setOrientationHint(CameraPolicy.normalizeRotation(sensorOrientation));
        mediaRecorder.setOutputFile(videoDescriptor.getFileDescriptor());
        mediaRecorder.prepare();
    }

    private void stopVideo(boolean userRequested) {
        if (!recording) {
            return;
        }
        long elapsed = Math.max(0L, System.currentTimeMillis() - recordingStartedAt);
        if (userRequested && !CameraPolicy.canStopVideo(true, elapsed)) {
            status.setText(R.string.status_video_too_short);
            return;
        }

        boolean saved = true;
        try {
            mediaRecorder.stop();
        } catch (RuntimeException exc) {
            saved = false;
        }
        recording = false;
        videoStarting = false;
        releaseRecorder();
        closeVideoDescriptor();
        if (captureSession != null) {
            captureSession.close();
            captureSession = null;
        }

        if (saved && pendingVideoUri != null) {
            ContentValues values = new ContentValues();
            values.put(MediaStore.Video.Media.IS_PENDING, 0);
            int updated = getContentResolver().update(pendingVideoUri, values, null, null);
            if (updated == 1) {
                status.setText(R.string.status_video_saved);
            } else {
                getContentResolver().delete(pendingVideoUri, null, null);
                status.setText(R.string.status_video_failed);
            }
        } else {
            if (pendingVideoUri != null) {
                getContentResolver().delete(pendingVideoUri, null, null);
            }
            status.setText(R.string.status_video_failed);
        }
        pendingVideoUri = null;
        refreshControls();
        startPreview();
    }

    private void abortPendingVideo() {
        videoStarting = false;
        recording = false;
        if (captureSession != null) {
            captureSession.close();
            captureSession = null;
        }
        releaseRecorder();
        closeVideoDescriptor();
        if (pendingVideoUri != null) {
            getContentResolver().delete(pendingVideoUri, null, null);
            pendingVideoUri = null;
        }
        refreshControls();
    }

    private void releaseRecorder() {
        if (mediaRecorder == null) {
            return;
        }
        try {
            mediaRecorder.reset();
        } catch (RuntimeException ignored) { }
        try {
            mediaRecorder.release();
        } catch (RuntimeException ignored) { }
        mediaRecorder = null;
    }

    private void closeVideoDescriptor() {
        if (videoDescriptor == null) {
            return;
        }
        try {
            videoDescriptor.close();
        } catch (IOException ignored) { }
        videoDescriptor = null;
    }

    private void switchCamera() {
        if (recording || videoStarting || pendingVideoUri != null || cameraCount < 2) {
            return;
        }
        preferFront = !preferFront;
        closeCamera();
        openCamera();
    }

    private void closeCamera() {
        if (captureSession != null) {
            captureSession.close();
            captureSession = null;
        }
        if (cameraDevice != null) {
            cameraDevice.close();
            cameraDevice = null;
        }
        if (imageReader != null) {
            imageReader.close();
            imageReader = null;
        }
        refreshControls();
    }

    private void refreshControls() {
        boolean ready = cameraDevice != null && captureSession != null && !videoStarting && !recording;
        if (photoButton != null) {
            photoButton.setEnabled(ready);
        }
        if (switchButton != null) {
            switchButton.setEnabled(ready && cameraCount > 1);
        }
        if (videoButton != null) {
            videoButton.setEnabled(recording || ready);
            videoButton.setText(recording ? R.string.stop_video : R.string.start_video);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) {
            return;
        }
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            status.setText(R.string.status_permission_granted);
            openCamera();
        } else {
            status.setText(R.string.status_permission_denied);
            refreshControls();
        }
    }
}
