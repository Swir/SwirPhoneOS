package org.swir.phoneos.backup;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

public final class MainActivity extends Activity {
    private static final int PICK_FILES = 70;
    private static final int CREATE_BACKUP = 71;
    private static final int INSPECT_BACKUP = 72;
    private final List<Uri> selected = new ArrayList<>();
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.addView(text(R.string.title, 28));
        root.addView(text(R.string.subtitle, 14));
        root.addView(text(R.string.safe_scope_notice, 13));
        Button pick = button(R.string.select_files);
        Button create = button(R.string.create_backup);
        Button inspect = button(R.string.inspect_backup);
        root.addView(pick); root.addView(create); root.addView(inspect);
        status = text(R.string.no_selection, 15);
        root.addView(status);
        setContentView(root);
        pick.setOnClickListener(v -> pickFiles());
        create.setOnClickListener(v -> chooseDestination());
        inspect.setOnClickListener(v -> chooseArchive());
    }

    private TextView text(int id, int sp) { TextView view = new TextView(this); view.setText(id); view.setTextSize(sp); view.setTextColor(Color.WHITE); view.setPadding(0, 6, 0, 10); return view; }
    private Button button(int id) { Button button = new Button(this); button.setText(id); return button; }

    private void pickFiles() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("*/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        startActivityForResult(intent, PICK_FILES);
    }

    private void chooseDestination() {
        if (selected.isEmpty()) { Toast.makeText(this, R.string.no_selection, Toast.LENGTH_LONG).show(); return; }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("application/zip");
        intent.putExtra(Intent.EXTRA_TITLE, BackupPolicy.backupFileName(System.currentTimeMillis()));
        startActivityForResult(intent, CREATE_BACKUP);
    }

    private void chooseArchive() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("application/zip");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, INSPECT_BACKUP);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null) return;
        if (requestCode == PICK_FILES) collectSelection(data);
        else if (requestCode == CREATE_BACKUP && data.getData() != null) writeBackup(data.getData());
        else if (requestCode == INSPECT_BACKUP && data.getData() != null) inspectBackup(data.getData());
    }

    private void collectSelection(Intent data) {
        selected.clear();
        ClipData clip = data.getClipData();
        if (clip != null) {
            for (int i = 0; i < clip.getItemCount() && selected.size() < BackupPolicy.MAX_FILES; i++) addUri(clip.getItemAt(i).getUri());
        } else addUri(data.getData());
        status.setText(getString(R.string.selection_count, selected.size()));
    }

    private void addUri(Uri uri) { if (uri != null && !selected.contains(uri) && selected.size() < BackupPolicy.MAX_FILES) selected.add(uri); }

    private void writeBackup(Uri destination) {
        status.setText(R.string.creating);
        executor.execute(() -> {
            try (OutputStream raw = getContentResolver().openOutputStream(destination, "w"); ZipOutputStream zip = raw == null ? null : new ZipOutputStream(raw)) {
                if (zip == null) throw new IllegalStateException();
                ZipEntry manifest = new ZipEntry("swir/manifest.txt");
                zip.putNextEntry(manifest);
                String metadata = "schema=1\nbuild=" + Build.FINGERPRINT + "\nsdk=" + Build.VERSION.SDK_INT + "\nfiles=" + selected.size() + "\n";
                zip.write(metadata.getBytes(StandardCharsets.UTF_8));
                zip.closeEntry();
                long total = 0;
                for (int i = 0; i < selected.size(); i++) {
                    Uri uri = selected.get(i);
                    DocumentInfo info = info(uri);
                    if (!BackupPolicy.sizeAllowed(info.size, total + Math.max(0, info.size))) throw new IllegalStateException();
                    String entryName = BackupPolicy.safeEntryName(info.name, i);
                    if (!BackupPolicy.validEntryName(entryName)) throw new IllegalStateException();
                    zip.putNextEntry(new ZipEntry(entryName));
                    long written = copyLimited(uri, zip, BackupPolicy.MAX_ENTRY_BYTES);
                    total += written;
                    if (!BackupPolicy.sizeAllowed(written, total)) throw new IllegalStateException();
                    zip.closeEntry();
                }
                zip.finish();
                runOnUiThread(() -> status.setText(R.string.backup_created));
            } catch (Exception error) {
                runOnUiThread(() -> status.setText(R.string.backup_failed));
            }
        });
    }

    private long copyLimited(Uri uri, OutputStream output, long limit) throws Exception {
        try (InputStream input = getContentResolver().openInputStream(uri)) {
            if (input == null) throw new IllegalStateException();
            byte[] buffer = new byte[8192]; long total = 0; int read;
            while ((read = input.read(buffer)) != -1) { total += read; if (total > limit) throw new IllegalStateException(); output.write(buffer, 0, read); }
            return total;
        }
    }

    private DocumentInfo info(Uri uri) {
        String name = null; long size = -1;
        try (Cursor cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) { name = cursor.getString(0); if (!cursor.isNull(1)) size = cursor.getLong(1); }
        }
        return new DocumentInfo(BackupPolicy.safeDisplayName(name), size);
    }

    private void inspectBackup(Uri uri) {
        status.setText(R.string.inspecting);
        executor.execute(() -> {
            int count = 0; long total = 0;
            try (InputStream raw = getContentResolver().openInputStream(uri); ZipInputStream zip = raw == null ? null : new ZipInputStream(raw)) {
                if (zip == null) throw new IllegalStateException();
                ZipEntry entry;
                byte[] buffer = new byte[8192];
                while ((entry = zip.getNextEntry()) != null) {
                    if (!BackupPolicy.validEntryName(entry.getName())) throw new IllegalStateException();
                    long entryBytes = 0; int read;
                    while ((read = zip.read(buffer)) != -1) { entryBytes += read; total += read; if (!BackupPolicy.sizeAllowed(entryBytes, total)) throw new IllegalStateException(); }
                    if (!entry.isDirectory()) count++;
                    if (count > BackupPolicy.MAX_FILES + 1) throw new IllegalStateException();
                    zip.closeEntry();
                }
                final int safeCount = count;
                runOnUiThread(() -> status.setText(getString(R.string.inspect_result, safeCount)));
            } catch (Exception error) {
                runOnUiThread(() -> status.setText(R.string.inspect_failed));
            }
        });
    }

    @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }

    private static final class DocumentInfo {
        final String name; final long size;
        DocumentInfo(String name, long size) { this.name = name; this.size = size; }
    }
}
