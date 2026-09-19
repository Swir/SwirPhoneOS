package org.swir.phoneos.update;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/**
 * In-memory, owner-driven review session for one exact local OTA package + detached manifest/signature.
 * Nothing in this class stages, installs, reboots, writes partitions or persists update artifacts.
 */
public final class OtaReviewSession {
    public static final int MAX_SIGNATURE_BYTES = 1024;

    public enum State {
        NEED_PACKAGE,
        PACKAGE_REJECTED,
        NEED_MANIFEST,
        MANIFEST_REJECTED,
        NEED_SIGNATURE,
        SIGNATURE_REJECTED,
        TRUST_REJECTED,
        MANIFEST_POLICY_REJECTED,
        AUTHENTIC_REVIEW_READY_NOT_STAGED
    }

    public static final class Review {
        private final State state;
        private final OtaTrustStore.ResolveState trustState;
        private final UpdatePolicy.ManifestState manifestState;

        Review(State state, OtaTrustStore.ResolveState trustState, UpdatePolicy.ManifestState manifestState) {
            this.state = state;
            this.trustState = trustState;
            this.manifestState = manifestState;
        }

        public State state() { return state; }
        public OtaTrustStore.ResolveState trustState() { return trustState; }
        public UpdatePolicy.ManifestState manifestState() { return manifestState; }
        public boolean authenticReviewReady() { return state == State.AUTHENTIC_REVIEW_READY_NOT_STAGED; }
        public boolean stagingAllowed() { return false; }
    }

    private String packageName = "";
    private UpdatePolicy.PackageInspection packageInspection;
    private byte[] manifestBytes;
    private byte[] signatureBytes;
    private UpdatePolicy.OtaManifest parsedManifest;
    private boolean manifestAttempted;
    private boolean signatureAttempted;

    public synchronized void clearPackage() {
        packageName = "";
        packageInspection = null;
        clearSignedArtifacts();
    }

    public synchronized void setPackage(String displayName, UpdatePolicy.PackageInspection inspection) {
        packageName = displayName == null ? "" : displayName;
        packageInspection = inspection;
        clearSignedArtifacts();
    }

    public synchronized boolean packageReady() {
        return packageInspection != null && packageInspection.reviewReady() && UpdatePolicy.safePackageName(packageName);
    }

    public synchronized boolean manifestReady() { return manifestBytes != null && parsedManifest != null; }
    public synchronized boolean signatureReady() { return signatureBytes != null && signatureBytes.length > 0; }

    public synchronized boolean selectManifest(InputStream input) {
        manifestAttempted = true;
        signatureAttempted = false;
        signatureBytes = null;
        byte[] candidate = readBounded(input, UpdatePolicy.MAX_MANIFEST_BYTES);
        UpdatePolicy.OtaManifest parsed = UpdatePolicy.parseCanonicalManifest(candidate);
        if (candidate == null || parsed == null) {
            manifestBytes = null;
            parsedManifest = null;
            return false;
        }
        manifestBytes = candidate;
        parsedManifest = parsed;
        return true;
    }

    public synchronized boolean selectSignature(InputStream input) {
        signatureAttempted = true;
        if (!manifestReady()) {
            signatureBytes = null;
            return false;
        }
        byte[] candidate = readBounded(input, MAX_SIGNATURE_BYTES);
        if (candidate == null || candidate.length == 0) {
            signatureBytes = null;
            return false;
        }
        signatureBytes = candidate;
        return true;
    }

    public synchronized UpdatePolicy.OtaManifest parsedManifest() { return parsedManifest; }
    public synchronized String manifestSha256() { return manifestBytes == null ? "" : UpdatePolicy.sha256Hex(manifestBytes); }
    public synchronized String signatureSha256() { return signatureBytes == null ? "" : UpdatePolicy.sha256Hex(signatureBytes); }

    public synchronized Review review(
            OtaTrustStore trustStore,
            String currentFingerprint,
            UpdatePolicy.Channel expectedChannel) {
        if (packageInspection == null) return new Review(State.NEED_PACKAGE, null, null);
        if (!packageReady()) return new Review(State.PACKAGE_REJECTED, null, null);
        if (manifestBytes == null || parsedManifest == null) {
            return new Review(manifestAttempted ? State.MANIFEST_REJECTED : State.NEED_MANIFEST, null, null);
        }
        if (signatureBytes == null || signatureBytes.length == 0) {
            return new Review(signatureAttempted ? State.SIGNATURE_REJECTED : State.NEED_SIGNATURE, null, null);
        }
        if (trustStore == null) return new Review(State.TRUST_REJECTED, OtaTrustStore.ResolveState.UNKNOWN_KEY, null);
        OtaTrustStore.ReviewResult result = trustStore.reviewSignedManifest(
                manifestBytes,
                signatureBytes,
                currentFingerprint,
                expectedChannel,
                packageName,
                packageInspection);
        if (result.authenticReviewReady()) {
            return new Review(
                    State.AUTHENTIC_REVIEW_READY_NOT_STAGED,
                    result.trustState(),
                    result.manifestReview() == null ? null : result.manifestReview().state());
        }
        if (result.trustState() != OtaTrustStore.ResolveState.TRUSTED) {
            return new Review(State.TRUST_REJECTED, result.trustState(), null);
        }
        return new Review(
                State.MANIFEST_POLICY_REJECTED,
                result.trustState(),
                result.manifestReview() == null ? null : result.manifestReview().state());
    }

    public static byte[] readBounded(InputStream input, int maxBytes) {
        if (input == null || maxBytes <= 0) return null;
        try {
            ByteArrayOutputStream output = new ByteArrayOutputStream(Math.min(maxBytes, 4096));
            byte[] buffer = new byte[4096];
            int total = 0;
            while (true) {
                if (Thread.currentThread().isInterrupted()) return null;
                int read = input.read(buffer);
                if (read < 0) break;
                if (read == 0) continue;
                if (read > maxBytes - total) return null;
                output.write(buffer, 0, read);
                total += read;
            }
            return total == 0 ? null : output.toByteArray();
        } catch (Exception ignored) {
            return null;
        }
    }

    private void clearSignedArtifacts() {
        manifestBytes = null;
        signatureBytes = null;
        parsedManifest = null;
        manifestAttempted = false;
        signatureAttempted = false;
    }
}
