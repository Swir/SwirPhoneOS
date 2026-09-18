package org.swir.phoneos.backup;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.provider.OpenableColumns;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
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
    private static final int PICK_RESTORE_BACKUP = 73;
    private static final int PICK_RESTORE_TREE = 74;
    private final List<Uri> selected = new ArrayList<>();
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private TextView status;
    private Uri pendingRestoreArchive;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_surface));
        int spaceXs = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(spaceMd, spaceMd, spaceMd, spaceMd);
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.addView(text(R.string.title, 28, spaceXs, spaceSm));
        TextView subtitle = text(R.string.subtitle, 14, spaceXs, spaceSm);
        subtitle.setTextColor(getColor(R.color.swir_text_secondary));
        root.addView(subtitle);
        TextView notice = text(R.string.safe_scope_notice, 13, spaceXs, spaceMd);
        notice.setTextColor(getColor(R.color.swir_text_secondary));
        root.addView(notice);

        Button pick = button(R.string.select_files);
        Button create = button(R.string.create_backup);
        Button inspect = button(R.string.inspect_backup);
        Button restore = button(R.string.restore_backup);
        root.addView(pick);
        root.addView(create);
        root.addView(inspect);
        root.addView(restore);
        status = text(R.string.no_selection, 15, spaceSm, spaceSm);
        status.setTextColor(getColor(R.color.swir_text_secondary));
        root.addView(status);
        setContentView(root);

        pick.setOnClickListener(v -> pickFiles());
        create.setOnClickListener(v -> chooseDestination());
        inspect.setOnClickListener(v -> chooseArchive());
        restore.setOnClickListener(v -> chooseRestoreArchive());
    }

    private TextView text(int id, int sp, int topPadding, int bottomPadding) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(getColor(R.color.swir_text_primary));
        view.setPadding(0, topPadding, 0, bottomPadding);
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
        button.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        return button;
    }

    private void pickFiles() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("*/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        startActivityForResult(intent, PICK_FILES);
    }

    private void chooseDestination() {
        if (selected.isEmpty()) {
            Toast.makeText(this, R.string.no_selection, Toast.LENGTH_LONG).show();
            return;
        }
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

    private void chooseRestoreArchive() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("application/zip");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, PICK_RESTORE_BACKUP);
    }

    private void chooseRestoreTree() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        startActivityForResult(intent, PICK_RESTORE_TREE);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null) return;
        if (requestCode == PICK_FILES) {
            collectSelection(data);
        } else if (requestCode == CREATE_BACKUP && data.getData() != null) {
            writeBackup(data.getData());
        } else if (requestCode == INSPECT_BACKUP && data.getData() != null) {
            inspectBackup(data.getData());
        } else if (requestCode == PICK_RESTORE_BACKUP && data.getData() != null) {
            pendingRestoreArchive = data.getData();
            status.setText(R.string.restore_destination);
            chooseRestoreTree();
        } else if (requestCode == PICK_RESTORE_TREE && data.getData() != null && pendingRestoreArchive != null) {
            Uri archive = pendingRestoreArchive;
            pendingRestoreArchive = null;
            restoreBackup(archive, data.getData());
        }
    }

    private void collectSelection(Intent data) {
        selected.clear();
        ClipData clip = data.getClipData();
        if (clip != null) {
            for (int i = 0; i < clip.getItemCount() && selected.size() < BackupPolicy.MAX_FILES; i++) {
                addUri(clip.getItemAt(i).getUri());
            }
        } else {
            addUri(data.getData());
        }
        status.setText(getString(R.string.selection_count, selected.size()));
    }

    private void addUri(Uri uri) {
        if (uri != null && !selected.contains(uri) && selected.size() < BackupPolicy.MAX_FILES) selected.add(uri);
    }

    private void writeBackup(Uri destination) {
        List<Uri> snapshot = new ArrayList<>(selected);
        status.setText(R.string.creating);
        executor.execute(() -> {
            try {
                ArrayList<PreparedDocument> prepared = prepareDocuments(snapshot);
                ArrayList<BackupPolicy.FileRecord> records = new ArrayList<>();
                for (PreparedDocument document : prepared) records.add(document.record);
                BackupPolicy.Manifest manifest = BackupPolicy.manifest(Build.FINGERPRINT, Build.VERSION.SDK_INT, records);
                byte[] manifestBytes = BackupPolicy.encodeManifest(manifest).getBytes(StandardCharsets.UTF_8);

                try (OutputStream raw = getContentResolver().openOutputStream(destination, "w");
                     ZipOutputStream zip = raw == null ? null : new ZipOutputStream(raw)) {
                    if (zip == null) throw new IllegalStateException("destination unavailable");
                    zip.putNextEntry(new ZipEntry(BackupPolicy.MANIFEST_ENTRY));
                    zip.write(manifestBytes);
                    zip.closeEntry();
                    for (PreparedDocument document : prepared) {
                        zip.putNextEntry(new ZipEntry(document.record.entryName));
                        DigestResult written;
                        try (InputStream input = getContentResolver().openInputStream(document.uri)) {
                            if (input == null) throw new IllegalStateException("source unavailable");
                            written = copyDigest(input, zip, BackupPolicy.MAX_ENTRY_BYTES);
                        }
                        requireIntegrity(document.record, written);
                        zip.closeEntry();
                    }
                    zip.finish();
                }
                runOnUiThread(() -> status.setText(R.string.backup_created));
            } catch (Exception error) {
                runOnUiThread(() -> status.setText(R.string.backup_failed));
            }
        });
    }

    private ArrayList<PreparedDocument> prepareDocuments(List<Uri> snapshot) throws Exception {
        if (snapshot.isEmpty() || snapshot.size() > BackupPolicy.MAX_FILES) throw new IllegalStateException("selection count");
        ArrayList<PreparedDocument> prepared = new ArrayList<>();
        long total = 0;
        for (int i = 0; i < snapshot.size(); i++) {
            Uri uri = snapshot.get(i);
            DocumentInfo info = info(uri);
            DigestResult digest;
            try (InputStream input = getContentResolver().openInputStream(uri)) {
                if (input == null) throw new IllegalStateException("source unavailable");
                digest = copyDigest(input, null, BackupPolicy.MAX_ENTRY_BYTES);
            }
            if (info.size >= 0 && info.size != digest.size) throw new IllegalStateException("source size changed");
            total += digest.size;
            if (!BackupPolicy.sizeAllowed(digest.size, total)) throw new IllegalStateException("selection too large");
            BackupPolicy.FileRecord record = new BackupPolicy.FileRecord(
                    BackupPolicy.safeEntryName(info.name, i), info.name, digest.size, digest.sha256);
            prepared.add(new PreparedDocument(uri, record));
        }
        return prepared;
    }

    private DocumentInfo info(Uri uri) {
        String name = null;
        long size = -1;
        try (Cursor cursor = getContentResolver().query(
                uri, new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                name = cursor.getString(0);
                if (!cursor.isNull(1)) size = cursor.getLong(1);
            }
        }
        return new DocumentInfo(BackupPolicy.safeDisplayName(name), size);
    }

    private void inspectBackup(Uri uri) {
        status.setText(R.string.inspecting);
        executor.execute(() -> {
            try {
                VerifiedArchive verified = verifyArchive(uri, true);
                if (verified.legacy) {
                    runOnUiThread(() -> status.setText(getString(R.string.inspect_legacy_result, verified.fileCount)));
                } else {
                    runOnUiThread(() -> status.setText(getString(R.string.inspect_verified_result, verified.fileCount)));
                }
            } catch (Exception error) {
                runOnUiThread(() -> status.setText(R.string.inspect_failed));
            }
        });
    }

    private VerifiedArchive verifyArchive(Uri uri, boolean allowLegacy) throws Exception {
        try (InputStream raw = getContentResolver().openInputStream(uri);
             ZipInputStream zip = raw == null ? null : new ZipInputStream(raw)) {
            if (zip == null) throw new IllegalStateException("archive unavailable");
            ZipEntry first = zip.getNextEntry();
            if (first == null || first.isDirectory() || !BackupPolicy.MANIFEST_ENTRY.equals(first.getName())) {
                throw new IllegalStateException("manifest must be first");
            }
            String text = new String(readBounded(zip, BackupPolicy.MAX_MANIFEST_BYTES), StandardCharsets.UTF_8);
            zip.closeEntry();
            if (BackupPolicy.isLegacyManifest(text)) {
                if (!allowLegacy) throw new IllegalStateException("legacy archive is inspect-only");
                int count = verifyLegacyEntries(zip);
                return new VerifiedArchive(null, true, count);
            }
            BackupPolicy.Manifest manifest = BackupPolicy.parseManifest(text);
            verifyManifestEntries(zip, manifest, null);
            return new VerifiedArchive(manifest, false, manifest.files.size());
        }
    }

    private int verifyLegacyEntries(ZipInputStream zip) throws Exception {
        int count = 0;
        long total = 0;
        ZipEntry entry;
        while ((entry = zip.getNextEntry()) != null) {
            if (entry.isDirectory() || !entry.getName().startsWith("files/") || !BackupPolicy.validEntryName(entry.getName())) {
                throw new IllegalStateException("legacy entry rejected");
            }
            DigestResult result = copyDigest(zip, null, BackupPolicy.MAX_ENTRY_BYTES);
            total += result.size;
            if (!BackupPolicy.sizeAllowed(result.size, total)) throw new IllegalStateException("legacy size limit");
            count++;
            if (count > BackupPolicy.MAX_FILES) throw new IllegalStateException("legacy count limit");
            zip.closeEntry();
        }
        return count;
    }

    private void verifyManifestEntries(ZipInputStream zip, BackupPolicy.Manifest manifest, RestoreWriter writer) throws Exception {
        long total = 0;
        for (BackupPolicy.FileRecord record : manifest.files) {
            ZipEntry entry = zip.getNextEntry();
            if (entry == null || entry.isDirectory() || !record.entryName.equals(entry.getName())) {
                throw new IllegalStateException("archive entry mismatch");
            }
            DigestResult result = writer == null
                    ? copyDigest(zip, null, BackupPolicy.MAX_ENTRY_BYTES)
                    : writer.write(record, zip);
            requireIntegrity(record, result);
            total += result.size;
            if (!BackupPolicy.sizeAllowed(result.size, total)) throw new IllegalStateException("archive size limit");
            zip.closeEntry();
        }
        if (zip.getNextEntry() != null) throw new IllegalStateException("unexpected archive entry");
    }

    private void restoreBackup(Uri archive, Uri treeUri) {
        status.setText(R.string.restoring);
        executor.execute(() -> {
            ArrayList<Uri> created = new ArrayList<>();
            try {
                VerifiedArchive verified = verifyArchive(archive, false);
                if (verified.manifest == null) throw new IllegalStateException("manifest missing");
                Uri parent = DocumentsContract.buildDocumentUriUsingTree(
                        treeUri, DocumentsContract.getTreeDocumentId(treeUri));
                BackupPolicy.Manifest expected = verified.manifest;

                try (InputStream raw = getContentResolver().openInputStream(archive);
                     ZipInputStream zip = raw == null ? null : new ZipInputStream(raw)) {
                    if (zip == null) throw new IllegalStateException("archive unavailable");
                    ZipEntry first = zip.getNextEntry();
                    if (first == null || !BackupPolicy.MANIFEST_ENTRY.equals(first.getName())) throw new IllegalStateException("manifest missing");
                    String secondText = new String(readBounded(zip, BackupPolicy.MAX_MANIFEST_BYTES), StandardCharsets.UTF_8);
                    zip.closeEntry();
                    BackupPolicy.Manifest second = BackupPolicy.parseManifest(secondText);
                    if (!BackupPolicy.encodeManifest(expected).equals(BackupPolicy.encodeManifest(second))) {
                        throw new IllegalStateException("archive changed before restore");
                    }
                    final int[] index = {0};
                    verifyManifestEntries(zip, second, (record, input) -> {
                        String tempName = String.format(java.util.Locale.ROOT, "swir-restore-%02d.part", index[0] + 1);
                        Uri temp = DocumentsContract.createDocument(getContentResolver(), parent, "application/octet-stream", tempName);
                        if (temp == null) throw new IllegalStateException("restore destination refused file");
                        created.add(temp);
                        DigestResult result;
                        try (OutputStream output = getContentResolver().openOutputStream(temp, "w")) {
                            if (output == null) throw new IllegalStateException("restore destination unavailable");
                            result = copyDigest(input, output, BackupPolicy.MAX_ENTRY_BYTES);
                        }
                        index[0]++;
                        return result;
                    });
                }

                ArrayList<Uri> finalized = new ArrayList<>();
                for (int i = 0; i < created.size(); i++) {
                    Uri renamed = DocumentsContract.renameDocument(
                            getContentResolver(), created.get(i), expected.files.get(i).displayName);
                    if (renamed == null) throw new IllegalStateException("restore rename failed");
                    finalized.add(renamed);
                    created.set(i, renamed);
                }
                final int restored = finalized.size();
                runOnUiThread(() -> status.setText(getString(R.string.restore_complete, restored)));
            } catch (Exception error) {
                cleanupDocuments(created);
                runOnUiThread(() -> status.setText(R.string.restore_failed));
            }
        });
    }

    private void cleanupDocuments(List<Uri> documents) {
        for (Uri uri : documents) {
            try { DocumentsContract.deleteDocument(getContentResolver(), uri); }
            catch (Exception ignored) { }
        }
    }

    private static byte[] readBounded(InputStream input, long limit) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        long total = 0;
        int read;
        while ((read = input.read(buffer)) != -1) {
            total += read;
            if (total > limit) throw new IllegalStateException("bounded read exceeded");
            output.write(buffer, 0, read);
        }
        return output.toByteArray();
    }

    private static DigestResult copyDigest(InputStream input, OutputStream output, long limit) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[8192];
        long total = 0;
        int read;
        while ((read = input.read(buffer)) != -1) {
            total += read;
            if (total > limit) throw new IllegalStateException("bounded copy exceeded");
            digest.update(buffer, 0, read);
            if (output != null) output.write(buffer, 0, read);
        }
        return new DigestResult(total, hex(digest.digest()));
    }

    private static void requireIntegrity(BackupPolicy.FileRecord record, DigestResult result) {
        if (record.size != result.size || !record.sha256.equals(result.sha256)) {
            throw new IllegalStateException("integrity mismatch");
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) out.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
        return out.toString();
    }

    @Override protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private interface RestoreWriter {
        DigestResult write(BackupPolicy.FileRecord record, InputStream input) throws Exception;
    }

    private static final class DocumentInfo {
        final String name;
        final long size;
        DocumentInfo(String name, long size) { this.name = name; this.size = size; }
    }

    private static final class PreparedDocument {
        final Uri uri;
        final BackupPolicy.FileRecord record;
        PreparedDocument(Uri uri, BackupPolicy.FileRecord record) { this.uri = uri; this.record = record; }
    }

    private static final class DigestResult {
        final long size;
        final String sha256;
        DigestResult(long size, String sha256) { this.size = size; this.sha256 = sha256; }
    }

    private static final class VerifiedArchive {
        final BackupPolicy.Manifest manifest;
        final boolean legacy;
        final int fileCount;
        VerifiedArchive(BackupPolicy.Manifest manifest, boolean legacy, int fileCount) {
            this.manifest = manifest;
            this.legacy = legacy;
            this.fileCount = fileCount;
        }
    }
}
