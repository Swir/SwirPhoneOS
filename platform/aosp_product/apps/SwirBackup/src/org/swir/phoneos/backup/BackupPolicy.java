package org.swir.phoneos.backup;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class BackupPolicy {
    public static final int MAX_FILES = 64;
    public static final long MAX_ENTRY_BYTES = 134_217_728L;
    public static final long MAX_TOTAL_BYTES = 536_870_912L;
    public static final int MAX_MANIFEST_BYTES = 65_536;
    public static final int MANIFEST_SCHEMA = 2;
    public static final String MANIFEST_ENTRY = "swir/manifest.txt";

    private BackupPolicy() {}

    public static boolean validEntryName(String name) {
        if (name == null || name.isEmpty() || name.length() > 180 || name.startsWith("/") || name.startsWith("\\")) return false;
        if (name.contains("\\") || name.contains("../") || name.equals("..") || name.contains("/../")) return false;
        for (int i = 0; i < name.length(); i++) if (Character.isISOControl(name.charAt(i))) return false;
        return true;
    }

    public static String safeDisplayName(String raw) {
        String value = raw == null ? "" : raw.trim();
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length() && out.length() < 96; i++) {
            char c = value.charAt(i);
            if (!Character.isISOControl(c) && c != '/' && c != '\\' && c != ':') out.append(c);
        }
        return out.length() == 0 ? "document" : out.toString();
    }

    public static String safeEntryName(String displayName, int index) {
        if (index < 0 || index >= MAX_FILES) return "";
        return String.format(Locale.ROOT, "files/%02d-%s", index + 1, safeDisplayName(displayName));
    }

    public static boolean sizeAllowed(long entryBytes, long totalBytes) {
        return entryBytes >= 0 && entryBytes <= MAX_ENTRY_BYTES && totalBytes >= 0 && totalBytes <= MAX_TOTAL_BYTES;
    }

    public static String backupFileName(long epochMillis) {
        return String.format(Locale.ROOT, "swir-backup-%d.swirbackup", Math.max(0L, epochMillis));
    }

    public static boolean validSha256(String value) {
        if (value == null || value.length() != 64) return false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
        }
        return true;
    }

    public static Manifest manifest(String buildFingerprint, int sdk, List<FileRecord> files) {
        String build = buildFingerprint == null ? "" : buildFingerprint;
        if (build.isEmpty() || build.length() > 512 || sdk < 1 || files == null || files.size() > MAX_FILES) {
            throw new IllegalArgumentException("invalid manifest header");
        }
        long total = 0;
        ArrayList<FileRecord> copy = new ArrayList<>();
        for (int i = 0; i < files.size(); i++) {
            FileRecord record = files.get(i);
            validateRecord(record, i);
            total += record.size;
            if (!sizeAllowed(record.size, total)) throw new IllegalArgumentException("manifest size limit");
            copy.add(record);
        }
        return new Manifest(build, sdk, copy);
    }

    public static String encodeManifest(Manifest manifest) {
        if (manifest == null) throw new IllegalArgumentException("manifest missing");
        Manifest checked = manifest(manifest.buildFingerprint, manifest.sdk, manifest.files);
        StringBuilder out = new StringBuilder();
        out.append("schema=").append(MANIFEST_SCHEMA).append('\n');
        out.append("build=").append(encodeField(checked.buildFingerprint)).append('\n');
        out.append("sdk=").append(checked.sdk).append('\n');
        out.append("files=").append(checked.files.size()).append('\n');
        for (int i = 0; i < checked.files.size(); i++) {
            FileRecord record = checked.files.get(i);
            String prefix = "file." + i + ".";
            out.append(prefix).append("entry=").append(encodeField(record.entryName)).append('\n');
            out.append(prefix).append("name=").append(encodeField(record.displayName)).append('\n');
            out.append(prefix).append("size=").append(record.size).append('\n');
            out.append(prefix).append("sha256=").append(record.sha256).append('\n');
        }
        byte[] encoded = out.toString().getBytes(StandardCharsets.UTF_8);
        if (encoded.length > MAX_MANIFEST_BYTES) throw new IllegalArgumentException("manifest too large");
        return out.toString();
    }

    public static Manifest parseManifest(String text) {
        if (text == null || text.getBytes(StandardCharsets.UTF_8).length > MAX_MANIFEST_BYTES) {
            throw new IllegalArgumentException("manifest too large");
        }
        LinkedHashMap<String, String> values = new LinkedHashMap<>();
        String[] lines = text.split("\\n", -1);
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            if (line.isEmpty() && i == lines.length - 1) continue;
            int equals = line.indexOf('=');
            if (equals <= 0 || equals == line.length() - 1) throw new IllegalArgumentException("malformed manifest");
            String key = line.substring(0, equals);
            String value = line.substring(equals + 1);
            if (values.put(key, value) != null) throw new IllegalArgumentException("duplicate manifest key");
        }
        if (!Integer.toString(MANIFEST_SCHEMA).equals(values.get("schema"))) throw new IllegalArgumentException("unsupported schema");
        int sdk = parseInt(values.get("sdk"), 1, Integer.MAX_VALUE, "sdk");
        int count = parseInt(values.get("files"), 0, MAX_FILES, "files");
        if (values.size() != 4 + count * 4) throw new IllegalArgumentException("unexpected manifest keys");
        String build = decodeField(values.get("build"));
        if (build.isEmpty() || build.length() > 512) throw new IllegalArgumentException("invalid build");
        ArrayList<FileRecord> records = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            String prefix = "file." + i + ".";
            String entry = decodeField(values.get(prefix + "entry"));
            String name = decodeField(values.get(prefix + "name"));
            long size = parseLong(values.get(prefix + "size"), 0, MAX_ENTRY_BYTES, "size");
            String sha = values.get(prefix + "sha256");
            FileRecord record = new FileRecord(entry, name, size, sha);
            validateRecord(record, i);
            records.add(record);
        }
        return manifest(build, sdk, records);
    }

    public static boolean isLegacyManifest(String text) {
        return text != null && text.startsWith("schema=1\n") && text.length() <= MAX_MANIFEST_BYTES;
    }

    private static void validateRecord(FileRecord record, int index) {
        if (record == null || record.entryName == null || record.displayName == null) throw new IllegalArgumentException("record missing");
        if (!record.displayName.equals(safeDisplayName(record.displayName))) throw new IllegalArgumentException("unsafe display name");
        if (!record.entryName.equals(safeEntryName(record.displayName, index)) || !validEntryName(record.entryName)) {
            throw new IllegalArgumentException("unsafe entry name");
        }
        if (!sizeAllowed(record.size, record.size) || !validSha256(record.sha256)) throw new IllegalArgumentException("invalid record integrity");
    }

    private static String encodeField(String value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static String decodeField(String value) {
        if (value == null || value.isEmpty() || value.length() > 1024) throw new IllegalArgumentException("invalid encoded field");
        try {
            String decoded = new String(Base64.getUrlDecoder().decode(value), StandardCharsets.UTF_8);
            if (!encodeField(decoded).equals(value)) throw new IllegalArgumentException("non-canonical field");
            return decoded;
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException("invalid encoded field", error);
        }
    }

    private static int parseInt(String value, int min, int max, String field) {
        try {
            int parsed = Integer.parseInt(value);
            if (parsed < min || parsed > max || !Integer.toString(parsed).equals(value)) throw new IllegalArgumentException(field);
            return parsed;
        } catch (RuntimeException error) {
            throw new IllegalArgumentException("invalid " + field, error);
        }
    }

    private static long parseLong(String value, long min, long max, String field) {
        try {
            long parsed = Long.parseLong(value);
            if (parsed < min || parsed > max || !Long.toString(parsed).equals(value)) throw new IllegalArgumentException(field);
            return parsed;
        } catch (RuntimeException error) {
            throw new IllegalArgumentException("invalid " + field, error);
        }
    }

    public static final class FileRecord {
        public final String entryName;
        public final String displayName;
        public final long size;
        public final String sha256;

        public FileRecord(String entryName, String displayName, long size, String sha256) {
            this.entryName = entryName;
            this.displayName = displayName;
            this.size = size;
            this.sha256 = sha256 == null ? "" : sha256.toLowerCase(Locale.ROOT);
        }
    }

    public static final class Manifest {
        public final String buildFingerprint;
        public final int sdk;
        public final List<FileRecord> files;

        private Manifest(String buildFingerprint, int sdk, List<FileRecord> files) {
            this.buildFingerprint = buildFingerprint;
            this.sdk = sdk;
            this.files = java.util.Collections.unmodifiableList(new ArrayList<>(files));
        }
    }
}
