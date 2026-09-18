package org.swir.phoneos.update;

import java.nio.charset.StandardCharsets;
import java.security.PublicKey;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Immutable, fail-closed OTA public-key registry.
 *
 * Only public verification keys belong here. Private signing material must never be shipped in the
 * OS image or repository. An entry is usable only when its canonical key id, RSA SubjectPublicKeyInfo
 * digest, lifecycle state and channel policy all match exactly.
 */
public final class OtaTrustStore {
    public static final String STORE_HEADER = "SWIR-OTA-TRUST-STORE-V1";
    public static final int MAX_KEYS = 32;

    public enum KeyStatus { ACTIVE, RETIRED, REVOKED }

    public enum ResolveState {
        TRUSTED,
        UNKNOWN_KEY,
        REVOKED_KEY,
        RETIRED_KEY,
        CHANNEL_NOT_ALLOWED,
        KEY_IDENTITY_INVALID
    }

    public static final class Entry {
        private final String keyId;
        private final PublicKey publicKey;
        private final String spkiSha256;
        private final KeyStatus status;
        private final EnumSet<UpdatePolicy.Channel> channels;

        public Entry(
                String keyId,
                PublicKey publicKey,
                String expectedSpkiSha256,
                KeyStatus status,
                EnumSet<UpdatePolicy.Channel> channels) {
            if (!safeKeyId(keyId)) throw new IllegalArgumentException("invalid key id");
            if (publicKey == null || !"RSA".equalsIgnoreCase(publicKey.getAlgorithm())) {
                throw new IllegalArgumentException("only RSA verification keys are accepted");
            }
            byte[] encoded = publicKey.getEncoded();
            if (encoded == null || encoded.length == 0) throw new IllegalArgumentException("missing public key encoding");
            if (!isLowerHexSha256(expectedSpkiSha256)) throw new IllegalArgumentException("invalid SPKI digest");
            String actualDigest = UpdatePolicy.sha256Hex(encoded);
            if (!expectedSpkiSha256.equals(actualDigest)) throw new IllegalArgumentException("SPKI digest mismatch");
            if (status == null) throw new IllegalArgumentException("missing key status");
            if (channels == null || channels.isEmpty() || channels.contains(UpdatePolicy.Channel.UNKNOWN)) {
                throw new IllegalArgumentException("invalid channel allowlist");
            }
            this.keyId = keyId;
            this.publicKey = publicKey;
            this.spkiSha256 = expectedSpkiSha256;
            this.status = status;
            this.channels = EnumSet.copyOf(channels);
        }

        public String keyId() { return keyId; }
        public PublicKey publicKey() { return publicKey; }
        public String spkiSha256() { return spkiSha256; }
        public KeyStatus status() { return status; }
        public Set<UpdatePolicy.Channel> channels() { return Collections.unmodifiableSet(channels); }

        boolean identityStillValid() {
            byte[] encoded = publicKey.getEncoded();
            return encoded != null && encoded.length > 0 && spkiSha256.equals(UpdatePolicy.sha256Hex(encoded));
        }
    }

    public static final class Resolution {
        private final ResolveState state;
        private final Entry entry;

        Resolution(ResolveState state, Entry entry) {
            this.state = state;
            this.entry = entry;
        }

        public ResolveState state() { return state; }
        public Entry entry() { return entry; }
        public boolean trusted() { return state == ResolveState.TRUSTED && entry != null; }
    }

    public static final class ReviewResult {
        private final ResolveState trustState;
        private final UpdatePolicy.ManifestReview manifestReview;

        ReviewResult(ResolveState trustState, UpdatePolicy.ManifestReview manifestReview) {
            this.trustState = trustState;
            this.manifestReview = manifestReview;
        }

        public ResolveState trustState() { return trustState; }
        public UpdatePolicy.ManifestReview manifestReview() { return manifestReview; }
        public boolean authenticReviewReady() {
            return trustState == ResolveState.TRUSTED
                    && manifestReview != null
                    && manifestReview.authenticReviewReady();
        }
        /** Trust review is never installation authorization. */
        public boolean stagingAllowed() { return false; }
    }

    private final List<Entry> entries;
    private final String canonicalDigest;

    public OtaTrustStore(List<Entry> entries) {
        if (entries == null || entries.size() > MAX_KEYS) throw new IllegalArgumentException("invalid trust store size");
        ArrayList<Entry> copy = new ArrayList<>(entries.size());
        HashSet<String> ids = new HashSet<>();
        for (Entry entry : entries) {
            if (entry == null) throw new IllegalArgumentException("null trust entry");
            if (!ids.add(entry.keyId())) throw new IllegalArgumentException("duplicate key id");
            copy.add(entry);
        }
        copy.sort(Comparator.comparing(Entry::keyId));
        this.entries = Collections.unmodifiableList(copy);
        this.canonicalDigest = UpdatePolicy.sha256Hex(canonicalBytes(copy));
    }

    public static OtaTrustStore empty() {
        return new OtaTrustStore(Collections.emptyList());
    }

    public int size() { return entries.size(); }
    public boolean hasProvisionedKeys() { return !entries.isEmpty(); }
    public String canonicalDigest() { return canonicalDigest; }
    public List<Entry> entries() { return entries; }

    public Resolution resolve(String keyId, UpdatePolicy.Channel channel) {
        if (!safeKeyId(keyId)) return new Resolution(ResolveState.UNKNOWN_KEY, null);
        Entry match = null;
        for (Entry entry : entries) {
            if (entry.keyId().equals(keyId)) {
                match = entry;
                break;
            }
        }
        if (match == null) return new Resolution(ResolveState.UNKNOWN_KEY, null);
        if (!match.identityStillValid()) return new Resolution(ResolveState.KEY_IDENTITY_INVALID, match);
        if (match.status() == KeyStatus.REVOKED) return new Resolution(ResolveState.REVOKED_KEY, match);
        if (match.status() == KeyStatus.RETIRED) return new Resolution(ResolveState.RETIRED_KEY, match);
        if (channel == null || channel == UpdatePolicy.Channel.UNKNOWN || !match.channels.contains(channel)) {
            return new Resolution(ResolveState.CHANNEL_NOT_ALLOWED, match);
        }
        return new Resolution(ResolveState.TRUSTED, match);
    }

    /**
     * Resolve the manifest key id through this immutable registry before signature verification.
     * Callers cannot inject an arbitrary verification key into this API.
     */
    public ReviewResult reviewSignedManifest(
            byte[] metadata,
            byte[] signature,
            String currentFingerprint,
            UpdatePolicy.Channel expectedChannel,
            String selectedPackageName,
            UpdatePolicy.PackageInspection packageInspection) {
        UpdatePolicy.OtaManifest manifest = UpdatePolicy.parseCanonicalManifest(metadata);
        if (manifest == null) {
            return new ReviewResult(
                    ResolveState.UNKNOWN_KEY,
                    new UpdatePolicy.ManifestReview(UpdatePolicy.ManifestState.REJECTED_FORMAT, null));
        }
        Resolution resolution = resolve(manifest.keyId(), expectedChannel);
        if (!resolution.trusted()) return new ReviewResult(resolution.state(), null);
        UpdatePolicy.ManifestReview review = UpdatePolicy.reviewSignedManifest(
                metadata,
                signature,
                resolution.entry().publicKey(),
                resolution.entry().keyId(),
                currentFingerprint,
                expectedChannel,
                selectedPackageName,
                packageInspection);
        return new ReviewResult(ResolveState.TRUSTED, review);
    }

    private static byte[] canonicalBytes(List<Entry> sortedEntries) {
        StringBuilder builder = new StringBuilder(STORE_HEADER);
        for (Entry entry : sortedEntries) {
            builder.append('\n')
                    .append(entry.keyId()).append('|')
                    .append(entry.status().name()).append('|')
                    .append(channelList(entry.channels)).append('|')
                    .append(entry.spkiSha256());
        }
        return builder.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static String channelList(EnumSet<UpdatePolicy.Channel> channels) {
        StringBuilder builder = new StringBuilder();
        for (UpdatePolicy.Channel channel : UpdatePolicy.Channel.values()) {
            if (channel == UpdatePolicy.Channel.UNKNOWN || !channels.contains(channel)) continue;
            if (builder.length() > 0) builder.append(',');
            builder.append(channel.name());
        }
        return builder.toString();
    }

    private static boolean safeKeyId(String value) {
        if (value == null || value.isEmpty() || value.length() > 128) return false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            boolean ok = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9')
                    || ch == '.' || ch == '_' || ch == '-';
            if (!ok) return false;
        }
        return true;
    }

    private static boolean isLowerHexSha256(String value) {
        if (value == null || value.length() != 64) return false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) return false;
        }
        return true;
    }
}