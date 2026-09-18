package org.swir.phoneos.update;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;

public final class OtaTrustStoreHostTest {
    public static void main(String[] args) throws Exception {
        KeyPair activePair = rsaPair();
        KeyPair revokedPair = rsaPair();
        KeyPair retiredPair = rsaPair();

        OtaTrustStore.Entry active = entry(
                "swir-beta-2026-01",
                activePair,
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.BETA));
        OtaTrustStore.Entry revoked = entry(
                "swir-revoked-2026-01",
                revokedPair,
                OtaTrustStore.KeyStatus.REVOKED,
                EnumSet.of(UpdatePolicy.Channel.BETA));
        OtaTrustStore.Entry retired = entry(
                "swir-retired-2025-01",
                retiredPair,
                OtaTrustStore.KeyStatus.RETIRED,
                EnumSet.of(UpdatePolicy.Channel.BETA));

        OtaTrustStore store = new OtaTrustStore(Arrays.asList(retired, active, revoked));
        check(store.size() == 3, "store size");
        check(store.hasProvisionedKeys(), "provisioned key state");
        check(store.canonicalDigest().length() == 64, "canonical digest");
        check(store.entries().get(0).keyId().equals("swir-beta-2026-01"), "canonical key ordering");
        check(store.resolve("swir-beta-2026-01", UpdatePolicy.Channel.BETA).trusted(), "active beta key trusted");
        check(store.resolve("missing-key", UpdatePolicy.Channel.BETA).state() == OtaTrustStore.ResolveState.UNKNOWN_KEY,
                "unknown key rejected");
        check(store.resolve("swir-revoked-2026-01", UpdatePolicy.Channel.BETA).state() == OtaTrustStore.ResolveState.REVOKED_KEY,
                "revoked key rejected");
        check(store.resolve("swir-retired-2025-01", UpdatePolicy.Channel.BETA).state() == OtaTrustStore.ResolveState.RETIRED_KEY,
                "retired key rejected");
        check(store.resolve("swir-beta-2026-01", UpdatePolicy.Channel.STABLE).state() == OtaTrustStore.ResolveState.CHANNEL_NOT_ALLOWED,
                "wrong channel rejected");
        check(store.resolve("swir-beta-2026-01", UpdatePolicy.Channel.UNKNOWN).state() == OtaTrustStore.ResolveState.CHANNEL_NOT_ALLOWED,
                "unknown channel rejected");

        OtaTrustStore empty = DefaultOtaTrustStore.create();
        check(empty.size() == 0, "default production store is intentionally empty");
        check(!empty.hasProvisionedKeys(), "no implicit production trust anchors");
        check(empty.resolve("swir-beta-2026-01", UpdatePolicy.Channel.BETA).state() == OtaTrustStore.ResolveState.UNKNOWN_KEY,
                "empty production store fails closed");

        byte[] candidate = new byte[]{0x50, 0x4b, 0x03, 0x04, 0x01, 0x02, 0x03, 0x04};
        UpdatePolicy.PackageInspection packageInspection = UpdatePolicy.inspectPackage(
                "swirphoneos-update.zip", candidate.length, new ByteArrayInputStream(candidate));
        check(packageInspection.reviewReady(), "package preflight ready");
        String current = "swir/device/product:17/CP2A.260605.016/1:userdebug/test-keys";
        String target = "swir/device/product:17/CP2A.260605.016/2:userdebug/release-keys";
        byte[] manifest = canonicalManifest(
                current,
                target,
                "swir-beta-2026-01",
                packageInspection);
        byte[] signature = sign(manifest, activePair);
        OtaTrustStore.ReviewResult ready = store.reviewSignedManifest(
                manifest,
                signature,
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                packageInspection);
        check(ready.trustState() == OtaTrustStore.ResolveState.TRUSTED, "trust resolution ready");
        check(ready.authenticReviewReady(), "trusted manifest review ready");
        check(ready.manifestReview().state() == UpdatePolicy.ManifestState.AUTHENTIC_REVIEW_READY_NOT_STAGED,
                "review remains not staged");
        check(!ready.stagingAllowed(), "trust store never authorizes staging");

        byte[] unknownKeyManifest = canonicalManifest(current, target, "unlisted-key", packageInspection);
        OtaTrustStore.ReviewResult unknown = store.reviewSignedManifest(
                unknownKeyManifest,
                sign(unknownKeyManifest, activePair),
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                packageInspection);
        check(unknown.trustState() == OtaTrustStore.ResolveState.UNKNOWN_KEY, "manifest cannot inject key id");
        check(!unknown.authenticReviewReady(), "unknown key cannot become authentic");

        byte[] revokedManifest = canonicalManifest(current, target, "swir-revoked-2026-01", packageInspection);
        OtaTrustStore.ReviewResult revokedResult = store.reviewSignedManifest(
                revokedManifest,
                sign(revokedManifest, revokedPair),
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                packageInspection);
        check(revokedResult.trustState() == OtaTrustStore.ResolveState.REVOKED_KEY, "revoked manifest rejected before trust");

        byte[] retiredManifest = canonicalManifest(current, target, "swir-retired-2025-01", packageInspection);
        OtaTrustStore.ReviewResult retiredResult = store.reviewSignedManifest(
                retiredManifest,
                sign(retiredManifest, retiredPair),
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                packageInspection);
        check(retiredResult.trustState() == OtaTrustStore.ResolveState.RETIRED_KEY, "retired manifest rejected before trust");

        byte[] tamperedSignature = signature.clone();
        tamperedSignature[0] ^= 1;
        OtaTrustStore.ReviewResult badSignature = store.reviewSignedManifest(
                manifest,
                tamperedSignature,
                current,
                UpdatePolicy.Channel.BETA,
                "swirphoneos-update.zip",
                packageInspection);
        check(badSignature.trustState() == OtaTrustStore.ResolveState.TRUSTED, "key remains trusted for signature test");
        check(badSignature.manifestReview().state() == UpdatePolicy.ManifestState.REJECTED_SIGNATURE,
                "bad signature rejected");

        expectIllegal(() -> new OtaTrustStore.Entry(
                "swir-beta-2026-02",
                activePair.getPublic(),
                repeat('0', 64),
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.BETA)), "SPKI mismatch rejected");
        expectIllegal(() -> new OtaTrustStore(Arrays.asList(active, active)), "duplicate key id rejected");
        expectIllegal(() -> new OtaTrustStore.Entry(
                "INVALID UPPER",
                activePair.getPublic(),
                UpdatePolicy.sha256Hex(activePair.getPublic().getEncoded()),
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.BETA)), "noncanonical key id rejected");
        expectIllegal(() -> new OtaTrustStore.Entry(
                "swir-unknown-channel",
                activePair.getPublic(),
                UpdatePolicy.sha256Hex(activePair.getPublic().getEncoded()),
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.UNKNOWN)), "UNKNOWN channel rejected");

        KeyPairGenerator ec = KeyPairGenerator.getInstance("EC");
        ec.initialize(256);
        KeyPair ecPair = ec.generateKeyPair();
        expectIllegal(() -> new OtaTrustStore.Entry(
                "swir-ec-key",
                ecPair.getPublic(),
                UpdatePolicy.sha256Hex(ecPair.getPublic().getEncoded()),
                OtaTrustStore.KeyStatus.ACTIVE,
                EnumSet.of(UpdatePolicy.Channel.BETA)), "non-RSA key rejected");

        check(new OtaTrustStore(Collections.singletonList(active)).canonicalDigest()
                        .equals(new OtaTrustStore(Collections.singletonList(active)).canonicalDigest()),
                "canonical store digest deterministic");
    }

    private static OtaTrustStore.Entry entry(
            String keyId,
            KeyPair pair,
            OtaTrustStore.KeyStatus status,
            EnumSet<UpdatePolicy.Channel> channels) {
        return new OtaTrustStore.Entry(
                keyId,
                pair.getPublic(),
                UpdatePolicy.sha256Hex(pair.getPublic().getEncoded()),
                status,
                channels);
    }

    private static KeyPair rsaPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair();
    }

    private static byte[] canonicalManifest(
            String current,
            String target,
            String keyId,
            UpdatePolicy.PackageInspection inspection) {
        String canonical = String.join("\n",
                UpdatePolicy.MANIFEST_HEADER,
                "source_fingerprint=" + current,
                "target_fingerprint=" + target,
                "channel=BETA",
                "package_name=swirphoneos-update.zip",
                "package_size=" + inspection.sizeBytes(),
                "package_sha256=" + inspection.sha256(),
                "key_id=" + keyId,
                "rollback_required=true");
        return canonical.getBytes(StandardCharsets.UTF_8);
    }

    private static byte[] sign(byte[] data, KeyPair pair) throws Exception {
        Signature signer = Signature.getInstance("SHA256withRSA");
        signer.initSign(pair.getPrivate());
        signer.update(data);
        return signer.sign();
    }

    private static String repeat(char ch, int count) {
        StringBuilder builder = new StringBuilder(count);
        for (int i = 0; i < count; i++) builder.append(ch);
        return builder.toString();
    }

    private static void expectIllegal(ThrowingRunnable runnable, String label) throws Exception {
        try {
            runnable.run();
        } catch (IllegalArgumentException expected) {
            return;
        }
        throw new AssertionError(label);
    }

    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }

    private interface ThrowingRunnable {
        void run() throws Exception;
    }
}