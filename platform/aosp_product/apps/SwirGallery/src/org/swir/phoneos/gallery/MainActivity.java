package org.swir.phoneos.gallery;

import android.Manifest;
import android.app.Activity;
import android.app.PendingIntent;
import android.content.ContentUris;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.format.Formatter;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Owner-visible local media browser using scoped MediaStore access only. */
public final class MainActivity extends Activity {
    private static final int PERMISSION_REQUEST = 6101;
    private static final int DELETE_REQUEST = 6102;
    private static final int MAX_ITEMS = 300;

    private final ArrayList<MediaItem> items = new ArrayList<>();
    private LinearLayout mediaList;
    private android.widget.EditText search;
    private TextView accessState;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
    }

    @Override protected void onStart() {
        super.onStart();
        refreshMedia();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST) {
            if (!hasAnyMediaPermission()) Toast.makeText(this, R.string.permission_denied, Toast.LENGTH_SHORT).show();
            refreshMedia();
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == DELETE_REQUEST) {
            Toast.makeText(this, resultCode == RESULT_OK ? R.string.delete_complete : R.string.delete_cancelled, Toast.LENGTH_SHORT).show();
            refreshMedia();
        }
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        root.addView(text(getString(R.string.app_name), 28, Color.rgb(105, 216, 255)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(180, 198, 217));
        subtitle.setPadding(0, dp(4), 0, dp(14));
        root.addView(subtitle, matchWrap());

        LinearLayout access = card();
        access.addView(text(getString(R.string.media_permission_title), 17, Color.rgb(105, 216, 255)), matchWrap());
        accessState = text(getString(R.string.media_permission_body), 14, Color.rgb(180, 198, 217));
        accessState.setPadding(0, dp(4), 0, dp(8));
        access.addView(accessState, matchWrap());
        LinearLayout actions = row();
        Button grant = button(R.string.grant_access);
        grant.setOnClickListener(v -> requestMediaPermissions());
        Button refresh = button(R.string.refresh);
        refresh.setOnClickListener(v -> refreshMedia());
        actions.addView(grant, weighted());
        actions.addView(refresh, weighted());
        access.addView(actions, matchWrap());
        root.addView(access, spaced());

        search = new android.widget.EditText(this);
        search.setHint(R.string.search_hint);
        search.setHintTextColor(Color.rgb(140, 160, 181));
        search.setTextColor(Color.WHITE);
        search.setSingleLine(true);
        search.setContentDescription(getString(R.string.search_hint));
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderMedia(); }
            @Override public void afterTextChanged(Editable s) {}
        });
        root.addView(search, spaced());

        mediaList = new LinearLayout(this);
        mediaList.setOrientation(LinearLayout.VERTICAL);
        root.addView(mediaList, matchWrap());

        TextView footer = text(getString(R.string.footer), 12, Color.rgb(140, 160, 181));
        footer.setPadding(0, dp(16), 0, 0);
        footer.setOnClickListener(v -> openGitHub());
        root.addView(footer, matchWrap());
        return scroll;
    }

    private void requestMediaPermissions() {
        requestPermissions(new String[]{Manifest.permission.READ_MEDIA_IMAGES, Manifest.permission.READ_MEDIA_VIDEO}, PERMISSION_REQUEST);
    }

    private boolean hasPermission(String permission) {
        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean hasAnyMediaPermission() {
        return hasPermission(Manifest.permission.READ_MEDIA_IMAGES) || hasPermission(Manifest.permission.READ_MEDIA_VIDEO);
    }

    private void refreshMedia() {
        boolean images = hasPermission(Manifest.permission.READ_MEDIA_IMAGES);
        boolean videos = hasPermission(Manifest.permission.READ_MEDIA_VIDEO);
        accessState.setText(images || videos ? R.string.permission_granted : R.string.media_permission_body);
        items.clear();
        if (!images && !videos) {
            renderMedia();
            return;
        }
        String selection;
        ArrayList<String> args = new ArrayList<>();
        if (images && videos) {
            selection = MediaStore.Files.FileColumns.MEDIA_TYPE + "=? OR " + MediaStore.Files.FileColumns.MEDIA_TYPE + "=?";
            args.add(Integer.toString(MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE));
            args.add(Integer.toString(MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO));
        } else {
            selection = MediaStore.Files.FileColumns.MEDIA_TYPE + "=?";
            args.add(Integer.toString(images ? MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE : MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO));
        }
        String[] projection = {
                MediaStore.MediaColumns._ID,
                MediaStore.MediaColumns.DISPLAY_NAME,
                MediaStore.MediaColumns.MIME_TYPE,
                MediaStore.MediaColumns.DATE_ADDED,
                MediaStore.MediaColumns.SIZE,
                MediaStore.Files.FileColumns.MEDIA_TYPE
        };
        Uri collection = MediaStore.Files.getContentUri("external");
        try (Cursor cursor = getContentResolver().query(collection, projection, selection, args.toArray(new String[0]), MediaStore.MediaColumns.DATE_ADDED + " DESC")) {
            if (cursor != null) {
                int idIndex = cursor.getColumnIndexOrThrow(MediaStore.MediaColumns._ID);
                int nameIndex = cursor.getColumnIndexOrThrow(MediaStore.MediaColumns.DISPLAY_NAME);
                int mimeIndex = cursor.getColumnIndexOrThrow(MediaStore.MediaColumns.MIME_TYPE);
                int dateIndex = cursor.getColumnIndexOrThrow(MediaStore.MediaColumns.DATE_ADDED);
                int sizeIndex = cursor.getColumnIndexOrThrow(MediaStore.MediaColumns.SIZE);
                int typeIndex = cursor.getColumnIndexOrThrow(MediaStore.Files.FileColumns.MEDIA_TYPE);
                while (cursor.moveToNext() && items.size() < MAX_ITEMS) {
                    long id = cursor.getLong(idIndex);
                    String name = cursor.getString(nameIndex);
                    String mime = cursor.getString(mimeIndex);
                    int mediaType = cursor.getInt(typeIndex);
                    if (!MediaPolicy.supportedMime(mime)) continue;
                    Uri uri = mediaType == MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO
                            ? ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, id)
                            : ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id);
                    items.add(new MediaItem(uri, name == null ? getString(R.string.unnamed) : name, mime,
                            MediaPolicy.safeEpochSeconds(cursor.getLong(dateIndex)), Math.max(0L, cursor.getLong(sizeIndex))));
                }
            }
        } catch (RuntimeException error) {
            Toast.makeText(this, R.string.media_load_failed, Toast.LENGTH_LONG).show();
        }
        renderMedia();
    }

    private void renderMedia() {
        if (mediaList == null) return;
        mediaList.removeAllViews();
        String query = search == null ? "" : search.getText().toString();
        int shown = 0;
        for (MediaItem item : items) {
            if (!MediaPolicy.matches(query, item.name, item.mime)) continue;
            mediaList.addView(mediaCard(item), spaced());
            shown++;
        }
        if (shown == 0) mediaList.addView(text(getString(R.string.empty), 14, Color.rgb(180, 198, 217)), spaced());
    }

    private View mediaCard(MediaItem item) {
        LinearLayout card = card();
        card.addView(text(item.name, 16, Color.WHITE), matchWrap());
        String type = getString(MediaPolicy.isVideo(item.mime) ? R.string.video : R.string.image);
        card.addView(text(getString(R.string.item_meta, type, Formatter.formatShortFileSize(this, item.size)), 13, Color.rgb(180, 198, 217)), matchWrap());
        LinearLayout actions = row();
        Button open = button(R.string.open);
        open.setOnClickListener(v -> openItem(item));
        Button share = button(R.string.share);
        share.setOnClickListener(v -> shareItem(item));
        Button delete = button(R.string.delete);
        delete.setOnClickListener(v -> requestDelete(item));
        actions.addView(open, weighted());
        actions.addView(share, weighted());
        actions.addView(delete, weighted());
        card.addView(actions, matchWrap());
        return card;
    }

    private void openItem(MediaItem item) {
        Intent intent = new Intent(Intent.ACTION_VIEW).setDataAndType(item.uri, item.mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.open_unavailable, Toast.LENGTH_SHORT).show();
    }

    private void shareItem(MediaItem item) {
        Intent intent = new Intent(Intent.ACTION_SEND).setType(item.mime).putExtra(Intent.EXTRA_STREAM, item.uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(Intent.createChooser(intent, getString(R.string.share_title)));
        else Toast.makeText(this, R.string.share_unavailable, Toast.LENGTH_SHORT).show();
    }

    private void requestDelete(MediaItem item) {
        try {
            PendingIntent request = MediaStore.createDeleteRequest(getContentResolver(), Collections.singletonList(item.uri));
            startIntentSenderForResult(request.getIntentSender(), DELETE_REQUEST, null, 0, 0, 0);
        } catch (Exception error) {
            Toast.makeText(this, R.string.delete_unavailable, Toast.LENGTH_SHORT).show();
        }
    }

    private void openGitHub() {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/Swir"));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private LinearLayout card() {
        LinearLayout value = new LinearLayout(this);
        value.setOrientation(LinearLayout.VERTICAL);
        value.setPadding(dp(14), dp(14), dp(14), dp(14));
        value.setBackgroundColor(Color.rgb(13, 34, 55));
        return value;
    }

    private LinearLayout row() {
        LinearLayout value = new LinearLayout(this);
        value.setOrientation(LinearLayout.HORIZONTAL);
        return value;
    }

    private Button button(int label) {
        Button value = new Button(this);
        value.setAllCaps(false);
        value.setText(label);
        value.setTextColor(Color.WHITE);
        value.setBackgroundColor(Color.rgb(17, 61, 92));
        value.setMinHeight(dp(48));
        return value;
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams spaced() {
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, 0, 0, dp(12));
        return params;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        params.setMargins(dp(3), dp(6), dp(3), 0);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class MediaItem {
        final Uri uri;
        final String name;
        final String mime;
        final long dateAdded;
        final long size;
        MediaItem(Uri uri, String name, String mime, long dateAdded, long size) {
            this.uri = uri;
            this.name = name;
            this.mime = mime;
            this.dateAdded = dateAdded;
            this.size = size;
        }
    }
}
